# -*- coding: utf-8 -*-
"""Р“РµРЅРµСЂР°С‚РѕСЂ РјРѕРґР° В«РЎРЎРЎР : Р’РµРє РЎС‚Р°Р»РёРЅР°В» РґР»СЏ HOI4 1.19.x.

Читает ванильные файлы, патчит их и собирает мод в папку игры.
Запуск: python gen.py
"""
import os, re, sys, io

GAME = r"D:\Hearts of Iron IV (2016)\Hearts of Iron IV"
MODROOT = os.path.join(os.path.expanduser("~"), "Documents", "Paradox Interactive",
                       "Hearts of Iron IV", "mod", "sov_stalin_expanded")
MODDIR = os.path.dirname(MODROOT)

def rd(p):
    with io.open(p, "r", encoding="utf-8-sig") as f:
        return f.read()

def wr(p, s, bom=False):
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(p, "w", encoding="utf-8-sig" if bom else "utf-8", newline="\n") as f:
        f.write(s)

import json as _json
_DP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_ru.json")
with io.open(_DP, encoding="utf-8") as _fh:
    DATA = _json.load(_fh)

def clean(line):
    line = re.sub(r'"[^"]*"', '""', line)
    return line.split("#", 1)[0]

def find_block(text, open_idx):
    """open_idx указывает на '{'. Возвращает индекс парной '}'."""
    depth = 0
    i = open_idx
    in_str = False
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "#":
            j = text.find("\n", i)
            if j < 0:
                return len(text) - 1
            i = j
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise RuntimeError("unbalanced braces")

def block_span(text, id_idx):
    """Границы блока focus, внутри которого встречается id_idx."""
    fs = text.rfind("focus = {", 0, id_idx)
    if fs < 0:
        raise RuntimeError("focus start not found")
    o = text.index("{", fs)
    c = find_block(text, o)
    return o, c

# ---------------------------------------------------------------- данные фокусов

def parse_focus_positions(text):
    res = {}
    for m in re.finditer(r"(?m)^\tfocus = \{", text):
        o = text.index("{", m.start())
        d = 0; i = o; ins = False
        while i < len(text):
            ch = text[i]
            if ins:
                if ch == '"': ins = False
            elif ch == '"': ins = True
            elif ch == "#":
                j = text.find("\n", i)
                i = len(text) if j < 0 else j
                continue
            elif ch == "{": d += 1
            elif ch == "}":
                d -= 1
                if d == 0: break
            i += 1
        blk = text[o:i + 1]
        fid = re.search(r"(?m)^\s*id = (\w+)", blk)
        if not fid: continue
        x = re.search(r"(?m)^\s*x = (-?\d+)", blk)
        y = re.search(r"(?m)^\s*y = (-?\d+)", blk)
        rel = re.search(r"(?m)^\s*relative_position_id = (\w+)", blk)
        res[fid.group(1)] = (int(x.group(1)) if x else 0,
                             int(y.group(1)) if y else 0,
                             rel.group(1) if rel else None)
    return res


def abs_positions(pos):
    memo = {}
    def g(fid, seen=()):
        if fid in memo: return memo[fid]
        if fid in seen or fid not in pos: return (0, 0)
        x, y, rel = pos[fid]
        if rel:
            px, py = g(rel, seen + (fid,))
            v = (px + x, py + y)
        else:
            v = (x, y)
        memo[fid] = v
        return v
    return {k: g(k) for k in pos}


VAN_POS = abs_positions(parse_focus_positions(
    rd(os.path.join(GAME, "common", "national_focus", "soviet.txt"))))


FX = {
 "prod":"industrial_capacity_factory","build":"production_speed_buildings_factor",
 "civil":"production_speed_industrial_complex_factor","arms":"production_speed_arms_factory_factor",
 "cg":"consumer_goods_factor","slots":"global_building_slots_factor",
 "cap":"production_factory_max_efficiency_factor","gain":"production_factory_efficiency_gain_factor",
 "res":"research_speed_factor","loc":"local_resources_factor","rep":"repair_speed_factor",
 "mcp":"max_command_power","cpg":"command_power_gain","plan":"planning_speed","org":"army_org_factor",
 "brk":"breakthrough_factor","mor":"army_morale_factor","atk":"army_attack_factor","def":"army_defence_factor",
 "spd":"army_speed_factor","arm_atk":"army_armor_attack_factor","art_atk":"army_artillery_attack_factor",
 "air_atk":"air_attack_factor","air_def":"air_defence_factor","axp":"experience_gain_army_factor",
 "fxp":"experience_gain_air_factor","doc":"land_doctrine_cost_factor","sf":"special_forces_cap",
 "ops":"operative_slot","pp":"political_power_factor","stab":"stability_factor","ws":"war_support_factor",
 "drift":"communism_drift","pstab":"party_popularity_stability_factor","adv":"political_advisor_cost_factor",
 "comp":"compliance_gain","cons":"conscription","surr":"max_surrender_limit_offset",
 "inet":"intel_network_gain_factor","dec":"decryption_power","cry":"crypto_strength",
 "cint":"intelligence_agency_defense","iciv":"civilian_intel_to_others","iarm":"army_intel_to_others",
}

def F(i, n, d, p, dx, dy, pre, fx, extra="", desc="", sf="FOCUS_FILTER_POLITICAL"):
    return dict(id=i, name=n, days=d, parent=p, dx=dx, dy=dy, pre=pre, fx=fx,
                extra=extra, desc=desc, sf=sf)

IND = [
 F("SOV_stalin_labor_mobilization","РЎС‚Р°Р»РёРЅСЃРєР°СЏ РјРѕР±РёР»РёР·Р°С†РёСЏ С‚СЂСѓРґР°",56,"SOV_industrial_modernization",-8,1,[],
   {"prod":.05,"build":.05,"cg":.05,"stab":-.05},"","Трудовые мобилизации, трудовая повинность и ГУЛАГ как источник рабочей силы.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_gulag_construction","ГУЛАГ как стройбаза",63,"SOV_stalin_labor_mobilization",0,1,[],
   {"build":.10,"civil":.10,"stab":-.05},"","РЎС‚СЂРѕР№РєРё РќРљР’Р”: Р‘РµР»РѕРјРѕСЂРєР°РЅР°Р», РєР°РЅР°Р»С‹, РґРѕСЂРѕРіРё, РїСЂРѕРјС‹С€Р»РµРЅРЅС‹Рµ РѕР±СЉРµРєС‚С‹.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_labor_discipline","Трудовая дисциплина",28,"SOV_gulag_construction",0,1,[],
   {"cap":.10,"cg":-.05},"","Ужесточение дисциплины и норм выработки на предприятиях.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_stalin_great_construction","РЎС‚Р°Р»РёРЅСЃРєРёРµ СЃС‚СЂРѕР№РєРё",56,"SOV_stalin_labor_mobilization",0,1,[],
   {"slots":.10,"build":.05},"","Метро, каналы, ГЭС и заводы-гиганты первой половины 1930-х.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_metro_builders","Метрострой",21,"SOV_stalin_great_construction",0,1,[],
   {"stab":.05,"build":.05},"","Московское метро как витрина режима.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_electrification","Электрификация страны",56,"SOV_metro_builders",0,1,[],
   {"prod":.05,"res":.05},"","РџР»Р°РЅ Р“РћР­Р›Р Рћ Рё РµРіРѕ РїСЂРѕРґРѕР»Р¶РµРЅРёРµ: СЌРЅРµСЂРіРµС‚РёРєР° РєР°Рє Р±Р°Р·Р° РёРЅРґСѓСЃС‚СЂРёРё.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_nature_transformation","План преобразования природы",56,"SOV_metro_builders",0,1,[],
   {"stab":.05,"cons":.01},"","Лесополосы, пруды и травопольные севообороты 1948 года.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_second_industrialization","Вторая индустриализация",70,"SOV_stalin_labor_mobilization",0,1,[],
   {"prod":.10,"cap":.10},"","Новые пятилетки и перенос центра тяжести в восточные районы.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_urals_stronghold","Уральский кулак",56,"SOV_second_industrialization",0,1,[],
   {"arms":.10,"prod":.05},"","РЈСЂР°Р» РєР°Рє РіР»Р°РІРЅС‹Р№ Р°СЂСЃРµРЅР°Р»: РњР°РіРЅРёС‚РєР°, Р§РµР»СЏР±РёРЅСЃРє, РЎРІРµСЂРґР»РѕРІСЃРє.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_donbass_revival","Возрождение Донбасса",49,"SOV_second_industrialization",-2,1,[],
   {"prod":.05,"rep":.10,"loc":.03},"","Восстановление шахт и металлургии Донбасса.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_tankograd_leader","Танкоград вождя",56,"SOV_urals_stronghold",0,1,[],
   {"arms":.10,"cap":.05},"","Танковые заводы Урала и Поволжья.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_aviation_volga","Авиазаводы Поволжья",56,"SOV_urals_stronghold",2,1,[],
   {"arms":.05,"air_atk":.05},"","Эвакуация авиапромышленности и новые сборочные линии.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_stalin_prize","РЎС‚Р°Р»РёРЅСЃРєР°СЏ РїСЂРµРјРёСЏ",28,"SOV_stalin_labor_mobilization",2,1,[],
   {"res":.05},"add_tech_bonus = { name = SOV_stalin_prize_bonus bonus = 1 uses = 3 category = industry }","Премия за выдающиеся достижения в науке и технике.","FOCUS_FILTER_RESEARCH"),
 F("SOV_atomic_supervision","Атомный надзор",56,"SOV_stalin_prize",0,1,[],
   {"res":.05},"add_breakthrough_progress = { specialization = specialization_nuclear value = 0.5 }","Кураторство атомного проекта на высшем уровне.","FOCUS_FILTER_RESEARCH"),
 F("SOV_gosplan_leader","Госплан вождя",49,"SOV_labor_discipline",0,1,[],
   {"cap":.05,"cg":-.05,"pp":.05},"","Госплан как инструмент ручного управления экономикой.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_kolkhoz_consolidation","Укрупнение колхозов",49,"SOV_gosplan_leader",0,1,[],
   {"cg":-.10,"cons":.01,"stab":-.05},"","Укрупнение хозяйств и изъятие ресурсов из деревни.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_fifth_five_year_plan","Пятая пятилетка",70,"SOV_second_industrialization",-2,2,["SOV_stalin_labor_mobilization"],
   {"prod":.10,"build":.10},"","Послевоенная пятилетка восстановления и роста.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_war_industry_mobilization","Мобилизация промышленности",70,"SOV_tankograd_leader",0,2,["SOV_aviation_volga"],
   {"arms":.10,"prod":.05,"cg":-.05},"","Перевод всей промышленности на военные рельсы.","FOCUS_FILTER_INDUSTRY"),
 # разведка и ресурсы — промка
 F("SOV_geology_survey","Геологическая разведка",35,"SOV_stalin_labor_mobilization",4,1,[],
   {"loc":.05,"res":.03},"","Массовые геологоразведочные партии 1930-х.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_urals_oil","Второе Баку",56,"SOV_geology_survey",0,1,[],
   {"loc":.05,"prod":.03},"","Освоение нефтяных месторождений Башкирии и Татарии.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_kuzbass","Кузбасс",49,"SOV_geology_survey",-2,1,[],
   {"loc":.05,"prod":.05},"","Уголь и металл Кузбасса.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_norilsk","Норильск",63,"SOV_kuzbass",0,1,[],
   {"loc":.05,"rep":.05,"stab":-.03},"","Норильский комбинат: никель, медь, кобальт.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_uranium_prospecting","Урановые месторождения",56,"SOV_geology_survey",2,1,[],
   {"loc":.03},"add_breakthrough_progress = { specialization = specialization_nuclear value = 0.3 }","Поиск и добыча урана для атомного проекта.","FOCUS_FILTER_RESEARCH"),
 F("SOV_rare_earth","Р РµРґРєРѕР·РµРјРµР»СЊРЅС‹Рµ РјРµС‚Р°Р»Р»С‹",49,"SOV_geology_survey",0,1,[],
   {"loc":.05,"prod":.03},"","Вольфрам, молибден, титан — основа брони и авиации.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_resource_expeditions","Экспедиции Академии наук",35,"SOV_geology_survey",2,1,[],
   {"res":.03,"loc":.03},"","Комплексные экспедиции по всей стране.","FOCUS_FILTER_RESEARCH"),
]

MIL = [
 F("SOV_general_staff","Генеральный штаб",56,"SOV_rehabilitated_military",0,1,[],
   {"mcp":20,"cpg":.5,"plan":.05},"","Р РµРѕСЂРіР°РЅРёР·Р°С†РёСЏ Р“РµРЅС€С‚Р°Р±Р° Рё РѕРїРµСЂР°С‚РёРІРЅРѕРіРѕ РїР»Р°РЅРёСЂРѕРІР°РЅРёСЏ.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_front_hqs","Штабы фронтов",49,"SOV_general_staff",0,1,[],
   {"mcp":10,"org":.05},"","Полевые штабы и управление фронтами.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_deep_operation","Глубокая операция",70,"SOV_front_hqs",0,1,[],
   {"brk":.10,"org":.05},"","Теория глубокой наступательной операции.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_victory_doctrine","Доктрина победы",70,"SOV_deep_operation",0,1,[],
   {"ws":.10,"mor":.05},"","Обобщение опыта войны в уставах.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_officer_rehabilitation","Р РµР°Р±РёР»РёС‚Р°С†РёСЏ РѕС„РёС†РµСЂРѕРІ",56,"SOV_general_staff",-2,1,[],
   {"axp":.10,"org":.05},"","Возвращение в строй уцелевших после чисток командиров.","FOCUS_FILTER_MANPOWER"),
 F("SOV_military_academies","Военные академии",49,"SOV_officer_rehabilitation",0,1,[],
   {"doc":-.10,"axp":.10},"","Академии Генштаба, бронетанковых и воздушных сил.","FOCUS_FILTER_RESEARCH"),
 F("SOV_military_courts","Военно-полевые суды",14,"SOV_general_staff",-2,2,[],
   {"org":.05,"stab":-.05},"","Дисциплина через страх: трибуналы и приказы.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_order_227","Приказ №227",14,"SOV_general_staff",0,2,[],
   {"ws":.10,"stab":-.05,"org":.03},"","«Ни шагу назад»: заградотряды и штрафбатальоны.","FOCUS_FILTER_WAR_SUPPORT"),
 F("SOV_tank_armies","Танковые армии",49,"SOV_front_hqs",2,1,[],
   {"arm_atk":.10,"spd":.03},"","Формирование танковых армий однородного состава.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_air_armies","Воздушные армии",49,"SOV_front_hqs",2,2,[],
   {"air_atk":.10,"air_def":.05},"","Воздушные армии фронтов.","FOCUS_FILTER_AIR_XP"),
 F("SOV_artillery_reserve","Артиллерия резерва",49,"SOV_front_hqs",2,3,[],
   {"art_atk":.10,"def":.03},"","РђСЂС‚РёР»Р»РµСЂРёР№СЃРєРёРµ РєРѕСЂРїСѓСЃР° Р Р’Р“Рљ.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_moscow_air_defense","ПВО Москвы",14,"SOV_air_armies",0,1,[],
   {"air_def":.10},"","Московская зона ПВО.","FOCUS_FILTER_AIR_XP"),
 F("SOV_stalin_falcons","РЎС‚Р°Р»РёРЅСЃРєРёРµ СЃРѕРєРѕР»С‹",14,"SOV_air_armies",0,2,[],
   {"fxp":.10,"air_atk":.05},"","Массовая подготовка лётчиков.","FOCUS_FILTER_AIR_XP"),
 F("SOV_rocket_program","Р Р°РєРµС‚РЅР°СЏ РїСЂРѕРіСЂР°РјРјР°",56,"SOV_military_academies",0,1,[],
   {"res":.05},"add_breakthrough_progress = { specialization = specialization_air value = 0.3 }","Р Р°РєРµС‚РЅС‹Рµ РёРЅСЃС‚РёС‚СѓС‚С‹ Рё РїРµСЂРІС‹Рµ СЃРµСЂРёР№РЅС‹Рµ РѕР±СЂР°Р·С†С‹.","FOCUS_FILTER_RESEARCH"),
 F("SOV_nkvd_special_units","РЎРїРµС†РЅР°Р· РќРљР’Р”",49,"SOV_officer_rehabilitation",0,1,[],
   {"sf":.05,"iarm":.05},"","Отдельные бригады особого назначения.","FOCUS_FILTER_MANPOWER"),
 F("SOV_marshal_of_victory","Маршал Победы",70,"SOV_victory_doctrine",0,1,["SOV_deep_operation"],
   {"mcp":20,"plan":.10,"mor":.05},"","РЎС‚Р°Р»РёРЅ РєР°Рє Р’РµСЂС…РѕРІРЅС‹Р№ РіР»Р°РІРЅРѕРєРѕРјР°РЅРґСѓСЋС‰РёР№ Рё РјР°СЂС€Р°Р».","FOCUS_FILTER_ARMY_XP"),
 # разведка — военка
 F("SOV_intel_school","Р Р°Р·РІРµРґС€РєРѕР»Р°",35,"SOV_smersh",0,3,[],
   {"inet":.10,"dec":.05},"","Учебные центры разведки и диверсий.","FOCUS_FILTER_POLITICAL"),
 F("SOV_foreign_department","РРЅРѕСЃС‚СЂР°РЅРЅС‹Р№ РѕС‚РґРµР»",49,"SOV_intel_school",0,1,[],
   {"inet":.15,"iciv":.05},"","РРќРћ РќРљР’Р”: Р°РіРµРЅС‚СѓСЂР° Р·Р° СЂСѓР±РµР¶РѕРј.","FOCUS_FILTER_POLITICAL"),
 F("SOV_cryptology","Криптографический отдел",49,"SOV_intel_school",-2,1,[],
   {"dec":.10,"cry":.10},"","Дешифровка и защита своих каналов.","FOCUS_FILTER_RESEARCH"),
 F("SOV_radio_intercept","Р Р°РґРёРѕРїРµСЂРµС…РІР°С‚",35,"SOV_cryptology",0,1,[],
   {"dec":.05,"iarm":.05},"","РЎР»СѓР¶Р±Р° СЂР°РґРёРѕРїРµСЂРµС…РІР°С‚Р° Рё РїРµР»РµРЅРіР°С†РёРё.","FOCUS_FILTER_RESEARCH"),
 F("SOV_agent_networks","Агентурные сети",56,"SOV_foreign_department",0,1,[],
   {"inet":.10,"iciv":.05},"","Р РµР·РёРґРµРЅС‚СѓСЂС‹ РІ Р•РІСЂРѕРїРµ Рё РђР·РёРё.","FOCUS_FILTER_POLITICAL"),
 F("SOV_sabotage_schools","Диверсионные школы",49,"SOV_foreign_department",2,1,[],
   {"iarm":.05,"cint":-.05},"","Подготовка диверсантов и партизанских кадров.","FOCUS_FILTER_POLITICAL"),
 F("SOV_counterintel","Контрразведка",49,"SOV_cryptology",-2,2,[],
   {"cint":.15,"dec":.05},"","РЎРњР•Р РЁ Рё Р±РѕСЂСЊР±Р° СЃ Р°РіРµРЅС‚СѓСЂРѕР№ РїСЂРѕС‚РёРІРЅРёРєР°.","FOCUS_FILTER_POLITICAL"),
 F("SOV_illegal_residents","Нелегалы",56,"SOV_agent_networks",0,1,[],
   {"inet":.10,"dec":.05},"","Р Р°Р·РІРµРґС‡РёРєРё-РЅРµР»РµРіР°Р»С‹ Р±РµР· РґРёРїР»РѕРјР°С‚РёС‡РµСЃРєРѕРіРѕ РїСЂРёРєСЂС‹С‚РёСЏ.","FOCUS_FILTER_POLITICAL"),
]

IA = [
 F("SOV_postwar_restoration","Восстановление народного хозяйства",56,"SOV_expand_the_agitprop",0,1,[],
   {"prod":.05,"build":.05,"stab":.05},"","Восстановление городов и заводов после войны.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_monetary_reform","Денежная реформа",35,"SOV_postwar_restoration",0,1,[],
   {"stab":.10,"pp":.03,"cg":.05},"","Р РµС„РѕСЂРјР° 1947 РіРѕРґР°: РѕР±РјРµРЅ РґРµРЅРµРі Рё РѕС‚РјРµРЅР° РєР°СЂС‚РѕС‡РµРє.","FOCUS_FILTER_STABILITY"),
 F("SOV_ration_cards_end","Отмена карточек",28,"SOV_monetary_reform",0,1,[],
   {"cg":-.05,"stab":.05},"","Переход к свободной торговле и нормированному снабжению.","FOCUS_FILTER_STABILITY"),
 F("SOV_price_cuts","РЎРЅРёР¶РµРЅРёРµ С†РµРЅ",35,"SOV_ration_cards_end",0,1,[],
   {"stab":.05,"pp":.03},"","Ежегодные снижения цен 1947–1953 годов.","FOCUS_FILTER_STABILITY"),
 F("SOV_volga_don","Волго-Донской канал",63,"SOV_postwar_restoration",-2,1,[],
   {"build":.05,"loc":.05},"","Канал Волга–Дон и превращение Волги в транспортную артерию.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_kuibyshev_hydro","Куйбышевская ГЭС",63,"SOV_volga_don",0,1,[],
   {"prod":.05,"build":.05},"","Крупнейшая ГЭС Европы на Волге.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_stalin_plan_nature","План преобразования природы",56,"SOV_volga_don",0,2,[],
   {"stab":.05,"loc":.03,"cons":.01},"","Лесополосы и пруды 1948 года.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_atomic_institute","РРЅСЃС‚РёС‚СѓС‚ Р°С‚РѕРјРЅРѕР№ СЌРЅРµСЂРіРёРё",56,"SOV_postwar_restoration",2,1,[],
   {"res":.05},"add_breakthrough_progress = { specialization = specialization_nuclear value = 0.5 }","Курчатовский институт и первый реактор.","FOCUS_FILTER_RESEARCH"),
 F("SOV_rocket_industry","Р Р°РєРµС‚РЅР°СЏ РїСЂРѕРјС‹С€Р»РµРЅРЅРѕСЃС‚СЊ",56,"SOV_atomic_institute",0,1,[],
   {"res":.05},"add_breakthrough_progress = { specialization = specialization_air value = 0.4 }","РЎРµСЂРёР№РЅРѕРµ РїСЂРѕРёР·РІРѕРґСЃС‚РІРѕ СЂР°РєРµС‚.","FOCUS_FILTER_RESEARCH"),
 F("SOV_jet_aviation","Р РµР°РєС‚РёРІРЅР°СЏ Р°РІРёР°С†РёСЏ",49,"SOV_rocket_industry",0,1,[],
   {"air_atk":.05},"add_tech_bonus = { name = SOV_jet_bonus bonus = 1 uses = 2 category = air_equipment }","МиГ-15 и переход на реактивную тягу.","FOCUS_FILTER_RESEARCH"),
 F("SOV_academy_expansion","Р Р°СЃС€РёСЂРµРЅРёРµ РђРєР°РґРµРјРёРё РЅР°СѓРє",49,"SOV_postwar_restoration",2,2,[],
   {"res":.05},"add_research_slot = 1","РќРѕРІС‹Рµ РёРЅСЃС‚РёС‚СѓС‚С‹ Рё РѕС‚РґРµР»РµРЅРёСЏ РђРќ РЎРЎРЎР .","FOCUS_FILTER_RESEARCH"),
 F("SOV_stalin_prize_second","РЎС‚Р°Р»РёРЅСЃРєР°СЏ РїСЂРµРјРёСЏ II",28,"SOV_academy_expansion",0,1,[],
   {"res":.05},"add_tech_bonus = { name = SOV_prize2_bonus bonus = 1 uses = 2 category = industry }","Вторая волна премий за науку и технику.","FOCUS_FILTER_RESEARCH"),
 F("SOV_michurin_biology","Мичуринская биология",35,"SOV_academy_expansion",0,2,[],
   {"stab":.03,"cons":.01,"res":-.05},"","Лысенко и мичуринская агробиология: плюс к урожаю, минус к науке.","FOCUS_FILTER_RESEARCH"),
 F("SOV_mgb_creation","МГБ",49,"SOV_postwar_restoration",-2,2,[],
   {"pp":.05,"cint":.05},"","Министерство госбезопасности как отдельная структура.","FOCUS_FILTER_POLITICAL"),
 F("SOV_border_troops","Пограничные войска",35,"SOV_mgb_creation",0,1,[],
   {"def":.05,"stab":.03},"","Пограничные округа и заставы.","FOCUS_FILTER_ARMY_XP"),
 F("SOV_gulag_expansion","Р Р°СЃС€РёСЂРµРЅРёРµ Р“РЈР›РђР“Р°",49,"SOV_mgb_creation",-2,1,[],
   {"build":.10,"stab":-.05},"","Лагерная экономика после войны.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_leningrad_affair","Ленинградское дело",28,"SOV_mgb_creation",2,1,[],
   {"pp":.10,"stab":-.10},"SOV_purge_escalate_effect = yes","Дело 1949 года против партийной верхушки Ленинграда.","FOCUS_FILTER_POLITICAL"),
 F("SOV_cosmopolitan_campaign","Борьба с космополитизмом",28,"SOV_mgb_creation",2,2,[],
   {"drift":.05,"adv":.10,"res":-.05},"","Кампания против «безродных космополитов» в науке и искусстве.","FOCUS_FILTER_POLITICAL"),
 F("SOV_doctor_plot_1953","Дело врачей",14,"SOV_leningrad_affair",0,2,[],
   {"pp":.10,"stab":-.10},"SOV_purge_escalate_effect = yes","Дело 1953 года против кремлёвских врачей.","FOCUS_FILTER_POLITICAL"),
 F("SOV_short_course","Краткий курс ВКП(б)",35,"SOV_stalins_cult_of_personality",-2,1,[],
   {"pp":.10,"drift":.05},"","Канонический учебник истории партии 1938 года.","FOCUS_FILTER_POLITICAL"),
 F("SOV_socrealism_official","РЎРѕС†РёР°Р»РёСЃС‚РёС‡РµСЃРєРёР№ СЂРµР°Р»РёР·Рј",35,"SOV_postwar_restoration",0,2,[],
   {"stab":.05},"","Единый художественный метод и борьба с формализмом.","FOCUS_FILTER_STABILITY"),
 F("SOV_patriarchate","Восстановление патриаршества",35,"SOV_stalins_cult_of_personality",-2,2,[],
   {"stab":.05,"ws":.05},"","Встреча со священноначалием 1943 года и избрание патриарха.","FOCUS_FILTER_STABILITY"),
 F("SOV_atheist_campaign_2","Атеистическая кампания",28,"SOV_socrealism_official",0,1,[],
   {"drift":.05,"stab":-.05},"","Массовая антирелигиозная пропаганда.","FOCUS_FILTER_POLITICAL"),
 F("SOV_friendship_of_peoples","Дружба народов",49,"SOV_postwar_restoration",2,3,[],
   {"comp":.05,"stab":.05},"","РћС„РёС†РёР°Р»СЊРЅР°СЏ Р»РёРЅРёСЏ РЅР° СЃР±Р»РёР¶РµРЅРёРµ РЅР°СЂРѕРґРѕРІ РЎРЎРЎР .","FOCUS_FILTER_STABILITY"),
 F("SOV_stalin_skyscrapers","РЎС‚Р°Р»РёРЅСЃРєРёРµ РІС‹СЃРѕС‚РєРё",49,"SOV_friendship_of_peoples",0,1,[],
   {"stab":.05,"build":.05},"","РЎРµРјСЊ РІС‹СЃРѕС‚РѕРє РњРѕСЃРєРІС‹ РєР°Рє СЃРёРјРІРѕР» СЌРїРѕС…Рё.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_history_textbook","Учебник истории",35,"SOV_friendship_of_peoples",0,2,[],
   {"pp":.05,"drift":.05},"","Новая официальная версия истории страны.","FOCUS_FILTER_POLITICAL"),
 F("SOV_veterans_return","Возвращение фронтовиков",35,"SOV_postwar_restoration",0,3,[],
   {"stab":.05,"cons":.01},"","Демобилизация и возвращение солдат к мирной жизни.","FOCUS_FILTER_STABILITY"),
 F("SOV_housing_program","Жилищное строительство",49,"SOV_veterans_return",0,1,[],
   {"build":.10,"stab":.05},"","Массовое строительство жилья после войны.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_school_reform","Школьная реформа",35,"SOV_housing_program",0,1,[],
   {"res":.05,"pp":.03},"","Р Р°Р·РґРµР»СЊРЅРѕРµ РѕР±СѓС‡РµРЅРёРµ Рё С‚СЂСѓРґРѕРІРѕРµ РІРѕСЃРїРёС‚Р°РЅРёРµ.","FOCUS_FILTER_RESEARCH"),
 F("SOV_pioneers","Пионерская организация",28,"SOV_veterans_return",-2,1,[],
   {"drift":.05,"cons":.01},"","Массовая детская организация.","FOCUS_FILTER_POLITICAL"),
 F("SOV_sport_movement","Физкультура и спорт",14,"SOV_pioneers",0,1,[],
   {"stab":.05,"cons":.01},"","РЎРїР°СЂС‚Р°РєРёР°РґС‹ Рё РјР°СЃСЃРѕРІС‹Р№ СЃРїРѕСЂС‚.","FOCUS_FILTER_STABILITY"),
 F("SOV_legacy_father","Наследие Отца народов",70,"SOV_postwar_restoration",0,4,["SOV_friendship_of_peoples"],
   {"cons":.02,"comp":.05,"ws":.05},"","РС‚РѕРі СЌРїРѕС…Рё: СЃС‚СЂР°РЅР°, РєРѕС‚РѕСЂРѕР№ СѓРїСЂР°РІР»СЏРµС‚ РІРѕР¶РґСЊ.","FOCUS_FILTER_MANPOWER"),
 F("SOV_vozhd_eternal","Вождь всех времён",70,"SOV_legacy_father",0,1,[],
   {"pp":.10,"stab":.05,"surr":.05},"","Финальная точка культа.","FOCUS_FILTER_POLITICAL"),
]

# фокусы вместо убранных дублей
IND += [
 F("SOV_chemical_industry","Химическая промышленность",56,"SOV_second_industrialization",2,1,[],
   {"prod":.05,"cg":-.05,"res":.03},"","Удобрения, полимеры и синтетика для промышленности и армии.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_machine_tools","Станкостроение",56,"SOV_second_industrialization",2,2,[],
   {"cap":.08,"gain":.05,"prod":.03},"","Станки и инструмент — база для любого производства.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_tractor_plants","Тракторные заводы",49,"SOV_urals_stronghold",2,2,[],
   {"arms":.05,"spd":.05,"build":.05},"","Тракторные заводы как база моторизации армии.","FOCUS_FILTER_INDUSTRY"),
 F("SOV_titanium_metallurgy","Титановая металлургия",56,"SOV_urals_stronghold",-2,2,[],
   {"arms":.05,"arm_atk":.05,"loc":.03},"","Титан и легированные стали для брони и авиации.","FOCUS_FILTER_INDUSTRY"),
]
MIL += [
 F("SOV_radar_network","Радиолокационная сеть",49,"SOV_air_armies",2,1,[],
   {"air_def":.08,"dec":.08,"cint":.05},"","Станции раннего обнаружения и радиоперехват.","FOCUS_FILTER_RESEARCH"),
]
IA += [
 F("SOV_literacy_campaign","Ликвидация неграмотности",35,"SOV_postwar_restoration",2,3,[],
   {"res":.05,"pp":.03,"stab":.03},"","Всеобщее начальное обучение и ликбез.","FOCUS_FILTER_RESEARCH"),
 F("SOV_soviet_cinema","Советское кино",35,"SOV_socrealism_official",0,1,[],
   {"stab":.05,"pp":.03,"drift":.03},"","Кино как главный инструмент пропаганды эпохи.","FOCUS_FILTER_STABILITY"),
]

DROP = {"SOV_atomic_supervision", "SOV_atomic_institute", "SOV_uranium_prospecting",
        "SOV_nature_transformation", "SOV_stalin_plan_nature", "SOV_patriarchate",
        "SOV_urals_oil"}
IND = [f for f in IND if f["id"] not in DROP]
MIL = [f for f in MIL if f["id"] not in DROP]
IA = [f for f in IA if f["id"] not in DROP]

for f in IA:
    if f["id"] == "SOV_rocket_industry":
        f["parent"] = "SOV_postwar_restoration"

ALL = IND + MIL + IA

_POOL = ["pp", "stab", "ws", "comp"]
_BUILD = {
    "ind": [
        "random_owned_controlled_state = { add_building_construction = { type = industrial_complex level = 1 instant_build = yes } }",
        "random_owned_controlled_state = { add_building_construction = { type = industrial_complex level = 2 instant_build = yes } }",
        "add_offsite_building = { type = industrial_complex level = 1 }",
        "random_owned_controlled_state = { add_extra_state_shared_building_slots = 2 }",
        "random_owned_controlled_state = { add_building_construction = { type = infrastructure level = 1 instant_build = yes } }",
    ],
    "mil": [
        "random_owned_controlled_state = { add_building_construction = { type = arms_factory level = 1 instant_build = yes } }",
        "random_owned_controlled_state = { add_building_construction = { type = arms_factory level = 2 instant_build = yes } }",
        "add_offsite_building = { type = arms_factory level = 1 }",
        "random_owned_controlled_state = { add_building_construction = { type = air_base level = 1 instant_build = yes } }",
    ],
    "ia": [
        "random_owned_controlled_state = { add_extra_state_shared_building_slots = 2 }",
        "random_owned_controlled_state = { add_building_construction = { type = infrastructure level = 1 instant_build = yes } }",
        "random_owned_controlled_state = { add_building_construction = { type = industrial_complex level = 1 instant_build = yes } }",
    ],
    "int": [
        "random_owned_controlled_state = { add_extra_state_shared_building_slots = 1 }",
        "add_offsite_building = { type = industrial_complex level = 1 }",
    ],
}

_RES = [
    "random_owned_controlled_state = { add_resource = { type = steel amount = 4 } }",
    "random_owned_controlled_state = { add_resource = { type = oil amount = 4 } }",
    "random_owned_controlled_state = { add_resource = { type = aluminium amount = 3 } }",
    "random_owned_controlled_state = { add_resource = { type = tungsten amount = 3 } }",
    "random_owned_controlled_state = { add_resource = { type = chromium amount = 3 } }",
]

_EXTRA = [
    "add_tech_bonus = { name = SOV_mod_tech bonus = 0.5 uses = 1 category = industry }",
    "army_experience = 15",
    "air_experience = 15",
    "add_command_power = 15",
    "add_manpower = 5000",
    "add_equipment_to_stockpile = { type = infantry_equipment amount = 500 }",
    "add_tech_bonus = { name = SOV_mod_tech2 bonus = 0.5 uses = 1 category = land_doctrine }",
    "add_stability = 0.01",
]
for _i, _f in enumerate(ALL):
    if not any(k in _f["fx"] for k in _POOL):
        _k = _POOL[_i % len(_POOL)]
        _f["fx"][_k] = 0.02 if _k == "pp" else 0.01

INTEL_IDS = {"SOV_intel_school", "SOV_foreign_department", "SOV_cryptology",
             "SOV_radio_intercept", "SOV_agent_networks", "SOV_sabotage_schools",
             "SOV_counterintel", "SOV_illegal_residents", "SOV_radar_network"}
for _f in ALL:
    if _f["id"] in INTEL_IDS:
        _f["group"] = "int"
    elif _f in IND:
        _f["group"] = "ind"
    elif _f in MIL:
        _f["group"] = "mil"
    else:
        _f["group"] = "ia"

GROUP_KEYS = {}
for _g in ("ind", "mil", "ia", "int"):
    keys = set()
    for _f in ALL:
        if _f["group"] == _g:
            keys |= set(_f["fx"].keys())
    GROUP_KEYS[_g] = sorted(keys)
GROUP_KEYS["ia"] = sorted(set(GROUP_KEYS["ia"]) | {"cg", "adv", "pp", "cons"})

ROOT_FOCUS = {"SOV_stalin_labor_mobilization", "SOV_general_staff",
              "SOV_postwar_restoration", "SOV_intel_school"}

GROUP_ICON = {
    "ind": "GFX_idea_SOV_fourth_five_year_plan",
    "mil": "GFX_idea_SOV_ground_based_training",
    "ia": "GFX_idea_SOV_factionalism_modifier",
    "int": "GFX_idea_SOV_conspiracy_in_the_academy_army",
}

# ---------------------------------------------------------------- генерация фокусов

TT_LABELS = {'prod': 'промышленная мощь', 'build': 'скорость строительства', 'civil': 'скорость строительства гражданских заводов', 'arms': 'скорость военных заводов', 'cg': 'потребительские товары', 'slots': 'слоты зданий', 'cap': 'потолок эффективности производства', 'gain': 'рост эффективности', 'res': 'скорость исследований', 'loc': 'ресурсы', 'rep': 'скорость ремонта', 'mcp': 'максимальные командные очки', 'cpg': 'прирост командных очков', 'plan': 'скорость планирования', 'org': 'организация', 'brk': 'прорыв', 'mor': 'мораль', 'atk': 'атака', 'def': 'оборона', 'spd': 'скорость', 'arm_atk': 'атака брони', 'art_atk': 'атака артиллерии', 'air_atk': 'авиационная атака', 'air_def': 'ПВО', 'axp': 'армейский опыт', 'fxp': 'авиационный опыт', 'doc': 'стоимость доктрин', 'sf': 'лимит спецназа', 'ops': 'слот оперника', 'pp': 'политвласть', 'stab': 'стабильность', 'ws': 'военная поддержка', 'drift': 'дрейф коммунизма', 'pstab': 'партийная стабильность', 'adv': 'стоимость советников', 'comp': 'комплаенс', 'cons': 'призыв', 'surr': 'лимит капитуляции', 'inet': 'агентурная сеть', 'dec': 'дешифровка', 'cry': 'криптостойкость', 'cint': 'контрразведка', 'iciv': 'гражданская разведка', 'iarm': 'военная разведка'}


def focus_tt(f):
    parts = []
    for k, v in f["fx"].items():
        pct = int(round(v * 100))
        sign = "+" if pct > 0 else ""
        col = "\u00a7G" if pct > 0 else "\u00a7R"
        parts.append("%s%s%s%% %s\u00a7!" % (col, sign, pct, TT_LABELS.get(k, k)))
    parts.append("\u00a7Y+завод или слоты, +ресурсы\u00a7!")
    if f["extra"] and "technolog" not in f["extra"]:
        parts.append("особый эффект")
    return ", ".join(parts)


def focus_block(f):
    ic = "GFX_focus_generic_" + {
        "SOV_stalin_labor_mobilization":"stalinist_industry","SOV_gulag_construction":"workers",
        "SOV_labor_discipline":"public_works","SOV_stalin_great_construction":"industry_1",
        "SOV_metro_builders":"railroad","SOV_electrification":"electrification",
        "SOV_nature_transformation":"farmland","SOV_second_industrialization":"industry_2",
        "SOV_urals_stronghold":"steel_mill","SOV_donbass_revival":"mining_industry",
        "SOV_tankograd_leader":"tank_production","SOV_aviation_volga":"aircraft_production",
        "SOV_stalin_prize":"university_1","SOV_atomic_supervision":"nuclear_development",
        "SOV_gosplan_leader":"central_planning","SOV_kolkhoz_consolidation":"agricultural_subsidies",
        "SOV_fifth_five_year_plan":"industry_3","SOV_war_industry_mobilization":"military_industry",
        "SOV_geology_survey":"mineral_prospecting","SOV_urals_oil":"offshore_oil_rig",
        "SOV_kuzbass":"coal_mining","SOV_norilsk":"resource_extraction",
        "SOV_geology_survey":"uranium_extraction","SOV_rare_earth":"tungsten",
        "SOV_resource_expeditions":"hydroelectric_energy",
        "SOV_general_staff":"military_academy","SOV_front_hqs":"improve_the_administration",
        "SOV_deep_operation":"army_attack","SOV_victory_doctrine":"total_war",
        "SOV_officer_rehabilitation":"advisors","SOV_military_academies":"university_2",
        "SOV_military_courts":"court","SOV_order_227":"defensive_reorganization",
        "SOV_tank_armies":"tank_assault","SOV_air_armies":"air_bases",
        "SOV_artillery_reserve":"self_propelled_gun","SOV_moscow_air_defense":"air_defense",
        "SOV_stalin_falcons":"pilot_training","SOV_rocket_program":"jet_planes",
        "SOV_nkvd_special_units":"special_forces" if False else "secret_agent_operative",
        "SOV_marshal_of_victory":"soldier_salute",
        "SOV_intel_school":"secret_service_agency","SOV_foreign_department":"infiltration",
        "SOV_cryptology":"cryptologic_bomb","SOV_radio_intercept":"radio_communication",
        "SOV_agent_networks":"spy_network" if False else "infiltration",
        "SOV_sabotage_schools":"sabotage","SOV_counterintel":"national_security",
        "SOV_illegal_residents":"secret_agent_operative",
        "SOV_postwar_restoration":"economic_recovery","SOV_monetary_reform":"currency_reforms",
        "SOV_ration_cards_end":"price_controls","SOV_price_cuts":"devaluation",
        "SOV_volga_don":"public_works","SOV_kuibyshev_hydro":"hydroelectric_energy",
        "SOV_stalin_plan_nature":"modernize_agriculture_2",
        "SOV_atomic_institute":"nuclear_development","SOV_rocket_industry":"jet_planes",
        "SOV_jet_aviation":"multi_role_aircraft","SOV_academy_expansion":"university_3",
        "SOV_stalin_prize_second":"education","SOV_michurin_biology":"agricultural_subsidies",
        "SOV_mgb_creation":"secret_service_agency","SOV_border_troops":"home_defense",
        "SOV_gulag_expansion":"workers","SOV_leningrad_affair":"conspiracy",
        "SOV_cosmopolitan_campaign":"crush_the_military" if False else "communist",
        "SOV_doctor_plot_1953":"conspiracy","SOV_short_course":"communist",
        "SOV_socrealism_official":"public_meetings","SOV_patriarchate":"pope",
        "SOV_atheist_campaign_2":"fascist_propaganda","SOV_friendship_of_peoples":"red_flags",
        "SOV_stalin_skyscrapers":"low_cost_housing" if False else "industry_investment",
        "SOV_history_textbook":"printing_press","SOV_veterans_return":"manpower",
        "SOV_housing_program":"low_cost_housing","SOV_school_reform":"education",
        "SOV_pioneers":"worker_expansion","SOV_sport_movement":"full_employment",
        "SOV_chemical_industry":"industry_3","SOV_machine_tools":"mass_production",
        "SOV_tractor_plants":"truck","SOV_titanium_metallurgy":"steel_mill",
        "SOV_radar_network":"radio_communication","SOV_literacy_campaign":"education",
        "SOV_soviet_cinema":"public_meetings",
        "SOV_legacy_father":"stalinist_industry","SOV_vozhd_eternal":"soviet_politics",
    }[f["id"]]
    out = []
    out.append("\tfocus = {")
    out.append("\t\tid = " + f["id"])
    out.append("\t\ticon = " + ic)
    pres = list(f["pre"])
    if f["parent"] and f["parent"] not in pres:
        pres.insert(0, f["parent"])
    for p in pres:
        out.append("\t\tprerequisite = { focus = %s }" % p)
    out.append("\t\tx = %d" % f["dx"])
    out.append("\t\ty = %d" % f["dy"])
    if f["parent"]:
        out.append("\t\trelative_position_id = " + f["parent"])
    out.append("\t\tcost = %d" % max(2, f["days"] // 7))
    out.append("\t\tavailable = {")
    out.append("\t\t\thas_country_leader = { character = SOV_iosif_stalin }")
    out.append("\t\t}")
    out.append("\t\tsearch_filters = { %s }" % f["sf"])
    out.append("\t\tai_will_do = { factor = 5 }")
    out.append("\t\tcompletion_reward = {")
    for k, v in f["fx"].items():
        out.append("\t\t\tadd_to_variable = { SOV_%s_%s = %s }" % (f["group"], k, v))
    if f["extra"]:
        for line in f["extra"].split("\n"):
            out.append("\t\t\t" + line)
    idx = sum(ord(c) for c in f["id"])
    out.append("\t\t\t" + _EXTRA[idx % len(_EXTRA)])
    out.append("\t\t\t" + _BUILD[f["group"]][idx % len(_BUILD[f["group"]])])
    out.append("\t\t\t" + _RES[idx % len(_RES)])
    if f["id"] in ROOT_FOCUS:
        out.append("\t\t\tif = { limit = { NOT = { has_dynamic_modifier = { modifier = SOV_%s_dm } } } "
                   "add_dynamic_modifier = { modifier = SOV_%s_dm } }" % (f["group"], f["group"]))
    out.append("\t\t\tcustom_effect_tooltip = %s_tt" % f["id"])
    out.append("\t\t}")
    out.append("\t}")
    return "\n".join(out)

def spread_siblings():
    groups = {}
    for f in ALL:
        groups.setdefault((f["parent"], f["dx"], f["dy"]), []).append(f)
    for (p, dx, dy), fs in groups.items():
        if len(fs) > 1 and p:
            for i, f in enumerate(fs):
                f["dx"] = dx + i * 2 - (len(fs) - 1)


spread_siblings()
try:
    import json as _j
    _OV = _j.load(io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "overrides.json"),
                          encoding="utf-8"))
except Exception:
    _OV = {}
for _f in ALL:
    _d = _OV.get(_f["id"])
    if _d:
        _f["dx"] += _d[0]
        _f["dy"] += _d[1]

FOCUS_TEXT = "\n".join(focus_block(f) for f in ALL)


# ---------------------------------------------------------------- РЎРѓР В»РЎС“Р В¶Р ВµР В±Р Р…РЎвЂ№Р Вµ РЎвЂљР ВµР С”РЎРѓРЎвЂљРЎвЂ№
DM_TEXT = ""
for _g in ("ind", "mil", "ia", "int"):
    DM_TEXT += "SOV_%s_dm = {\n\tenable = { always = yes }\n\ticon = %s\n\n" % (_g, GROUP_ICON[_g])
    for _k in GROUP_KEYS[_g]:
        DM_TEXT += "\t%s = SOV_%s_%s\n" % (FX[_k], _g, _k)
    DM_TEXT += {"ind": "\tpolitical_power_factor = -0.02\n",
                "mil": "\tresearch_speed_factor = -0.02\n",
                "ia": "\tarmy_org_factor = -0.02\n",
                "int": "\tpolitical_power_factor = -0.01\n"}[_g]
    DM_TEXT += "}\n\n"

IDEAS_TEXT = """ideas = {
\tcountry = {

\t\tSOV_purge_spirit_1 = {
\t\t\tallowed = { always = no }
\t\t\tremoval_cost = -1
\t\t\tpicture = SOV_purged_junior_army_officers
\t\t\tmodifier = {
\t\t\t\tarmy_attack_factor = -0.05
\t\t\t\tarmy_defence_factor = -0.05
\t\t\t\tarmy_org_factor = -0.05
\t\t\t\texperience_gain_army_factor = -0.10
\t\t\t\tpolitical_power_factor = 0.05
\t\t\t\tstability_factor = 0.03
\t\t\t}
\t\t}

\t\tSOV_purge_spirit_2 = {
\t\t\tallowed = { always = no }
\t\t\tremoval_cost = -1
\t\t\tpicture = SOV_purged_junior_army_officers
\t\t\tmodifier = {
\t\t\t\tarmy_attack_factor = -0.10
\t\t\t\tarmy_defence_factor = -0.10
\t\t\t\tarmy_org_factor = -0.10
\t\t\t\texperience_gain_army_factor = -0.15
\t\t\t\tland_doctrine_cost_factor = 0.15
\t\t\t\tarmy_speed_factor = -0.05
\t\t\t\tpolitical_power_factor = 0.10
\t\t\t\tstability_factor = 0.05
\t\t\t}
\t\t}

\t\tSOV_purge_spirit_3 = {
\t\t\tallowed = { always = no }
\t\t\tremoval_cost = -1
\t\t\tpicture = SOV_purged_junior_army_officers
\t\t\tmodifier = {
\t\t\t\tarmy_attack_factor = -0.20
\t\t\t\tarmy_defence_factor = -0.20
\t\t\t\tarmy_org_factor = -0.20
\t\t\t\texperience_gain_army_factor = -0.25
\t\t\t\tland_doctrine_cost_factor = 0.30
\t\t\t\tarmy_speed_factor = -0.10
\t\t\t\tplanning_speed = -0.10
\t\t\t\tpolitical_power_factor = 0.15
\t\t\t\tstability_factor = 0.05
\t\t\t\tpolitical_advisor_cost_factor = 0.15
\t\t\t}
\t\t}
\t\tGER_sov_test_handicap = {
\t\t\tallowed = { always = no }
\t\t\tremoval_cost = -1
\t\t\tpicture = SOV_conspiracy_in_the_academy_army
\t\t\tmodifier = {
\t\t\t\tarmy_attack_factor = -0.20
\t\t\t\tarmy_defence_factor = -0.20
\t\t\t\tarmy_org_factor = -0.20
\t\t\t\tindustrial_capacity_factory = -0.15
\t\t\t\tproduction_speed_buildings_factor = -0.15
\t\t\t\twar_support_factor = -0.10
\t\t\t}
\t\t}
\t}
}
"""

EFFECTS_TEXT = """SOV_purge_escalate_effect = {
\tif = { limit = { check_variable = { SOV_purge_level < 3 } }
\t\tif = { limit = { has_idea = SOV_purge_spirit_1 } remove_ideas = SOV_purge_spirit_1 }
\t\telse_if = { limit = { has_idea = SOV_purge_spirit_2 } remove_ideas = SOV_purge_spirit_2 }
\t\telse_if = { limit = { has_idea = SOV_purge_spirit_3 } remove_ideas = SOV_purge_spirit_3 }
\t}

\tadd_to_variable = { SOV_purge_level = 1 }
\tclamp_variable = { var = SOV_purge_level min = 1 max = 3 }

\tif = { limit = { check_variable = { SOV_purge_level = 1 } }
\t\tadd_timed_idea = { idea = SOV_purge_spirit_1 days = 900 } }
\telse_if = { limit = { check_variable = { SOV_purge_level = 2 } }
\t\tadd_timed_idea = { idea = SOV_purge_spirit_2 days = 900 } }
\telse = {
\t\tadd_timed_idea = { idea = SOV_purge_spirit_3 days = 900 } }
}

SOV_purge_stop_effect = {
\tremove_ideas = SOV_purge_spirit_1
\tremove_ideas = SOV_purge_spirit_2
\tremove_ideas = SOV_purge_spirit_3
\tset_variable = { SOV_purge_level = 0 }
}
"""

PROP_CAMPAIGNS = [
 ("all_for_front","Р вЂ™РЎРѓРЎвЂ Р Т‘Р В»РЎРЏ РЎвЂћРЎР‚Р С•Р Р…РЎвЂљР В°",75,"war_support_factor = 0.10","add_stability = -0.05"),
 ("labor_discipline","Р СћРЎР‚РЎС“Р Т‘Р С•Р Р†Р В°РЎРЏ Р Т‘Р С‘РЎРѓРЎвЂ Р С‘Р С—Р В»Р С‘Р Р…Р В°",90,"industrial_capacity_factory = 0.05","add_to_variable = { SOV_ia_cg = 0.05 }"),
 ("leader_with_us","Р вЂ™Р С•Р В¶Р Т‘РЎРЉ РЎРѓ Р Р…Р В°Р СР С‘",80,"political_power_factor = 0.10","add_to_variable = { SOV_ia_adv = 0.05 }"),
 ("spy_mania","Р РЃР С—Р С‘Р С•Р Р…Р С•Р СР В°Р Р…Р С‘РЎРЏ",70,"intel_network_gain_factor = 0.10","add_stability = -0.05"),
 ("science_cult","Р С™РЎС“Р В»РЎРЉРЎвЂљ Р Р…Р В°РЎС“Р С”Р С‘",85,"research_speed_factor = 0.05","add_to_variable = { SOV_ia_pp = -0.05 }"),
 ("brotherhood","Р вЂРЎР‚Р В°РЎвЂљРЎРѓРЎвЂљР Р†Р С• Р Р…Р В°РЎР‚Р С•Р Т‘Р С•Р Р†",90,"compliance_gain = 0.05","add_to_variable = { SOV_ia_cg = 0.05 }"),
 ("stakhanov_call","Р РЋРЎвЂљР В°РЎвЂ¦Р В°Р Р…Р С•Р Р†РЎРѓР С”Р С‘Р в„– Р С—РЎР‚Р С‘Р В·РЎвЂ№Р Р†",95,"production_factory_max_efficiency_factor = 0.10","add_to_variable = { SOV_ia_cons = -0.01 }"),
 ("victory_poster","Р СџР В»Р В°Р С”Р В°РЎвЂљ Р С—Р С•Р В±Р ВµР Т‘РЎвЂ№",80,"war_support_factor = 0.05\n\t\tstability_factor = 0.05","add_to_variable = { SOV_ia_pp = -0.10 }"),
 ("atheist_campaign","Р С’Р Р…РЎвЂљР С‘РЎР‚Р ВµР В»Р С‘Р С–Р С‘Р С•Р В·Р Р…Р В°РЎРЏ Р С”Р В°Р СР С—Р В°Р Р…Р С‘РЎРЏ",70,"communism_drift = 0.05","add_stability = -0.05"),
 ("leader_youth","Р вЂ™Р С•Р В¶Р Т‘РЎРЉ Р С‘ Р СР С•Р В»Р С•Р Т‘РЎвЂР В¶РЎРЉ",75,"conscription = 0.01","add_to_variable = { SOV_ia_adv = 0.05 }"),
]

CAT_TEXT = """SOV_propaganda_extra = {
\tpriority = 99
\ticon = SOV_propaganda
\tallowed = { original_tag = SOV }
\tvisible = { always = yes }
}

SOV_resources_prospect = {
\tpriority = 98
\ticon = SOV_propaganda
\tallowed = { original_tag = SOV }
\tvisible = { always = yes }
}

"""

DEC_TEXT = "SOV_propaganda_campaigns = {\n"
for pid, name, cost, buff, debuff in PROP_CAMPAIGNS:
    DEC_TEXT += """SOV_prop_%s = {
\ticon = eng_propaganda_campaigns
\tallowed = { original_tag = SOV }
\tvisible = { always = yes }
\tai_will_do = { base = 0 }
\tavailable = { always = yes }
\tcost = %d
\tdays_remove = 120
\tdays_re_enable = 60
\tmodifier = {
\t\t%s
\t\tindustrial_capacity_factory = 0.05
\t\twar_support_factor = 0.05
\t\tstability_factor = 0.03
\t\tconsumer_goods_factor = -0.03
\t}
\tcomplete_effect = {
\t\t%s
\t}
\tremove_effect = { }
}

""" % (pid, cost, buff, debuff)
DEC_TEXT += "}\n\nprospect_for_resources = {\n"

RES_DEC = [
 ("oil","Р В Р В°Р В·Р Р†Р ВµР Т‘Р С”Р В° Р Р…Р ВµРЎвЂћРЎвЂљР С‘","oil",6),
 ("coal","Р В Р В°Р В·Р Р†Р ВµР Т‘Р С”Р В° РЎС“Р С–Р В»РЎРЏ","coal",6),
 ("steel","Р В Р В°Р В·Р Р†Р ВµР Т‘Р С”Р В° Р СР ВµРЎвЂљР В°Р В»Р В»Р В°","steel",6),
 ("aluminium","Р В Р В°Р В·Р Р†Р ВµР Т‘Р С”Р В° Р В±Р С•Р С”РЎРѓР С‘РЎвЂљР С•Р Р†","aluminium",4),
]
for rid, name, res, amt in RES_DEC:
    DEC_TEXT += """SOV_prospect_%s = {
\ticon = GFX_focus_generic_mineral_prospecting
\tallowed = { original_tag = SOV }
\tvisible = { always = yes }
\tai_will_do = { base = 0 }
\tavailable = {
\t\tany_owned_state = {
\t\t\tNOT = { has_state_flag = SOV_prospected_%s }
\t\t}
\t}
\tcost = 75
\tdays_remove = 90
\tdays_re_enable = 30
\tcomplete_effect = {
\t\trandom_owned_state = {
\t\t\tlimit = {
\t\t\t\tNOT = { has_state_flag = SOV_prospected_%s }
\t\t\t}
\t\t\tadd_resource = { type = %s amount = %d }
\t\t\tset_state_flag = SOV_prospected_%s
\t\t}
\t}
}

""" % (rid, rid, rid, res, amt, rid)
DEC_TEXT += "}\n"

# ---------------------------------------------------------------- Р В»Р С•Р С”Р В°Р В»Р С‘Р В·Р В°РЎвЂ Р С‘РЎРЏ
LOC = "l_russian:\n"
for f in ALL:
    n, d = DATA["focuses"][f["id"]]
    LOC += ' %s: "%s"\n' % (f["id"], n)
    LOC += ' %s_desc: "%s"\n' % (f["id"], d)
    LOC += ' %s_tt: "%s"\n' % (f["id"], focus_tt(f))
for lvl in ("1", "2", "3"):
    n, d = DATA["purge"][lvl]
    LOC += ' SOV_purge_spirit_%s: "%s"\n' % (lvl, n)
    LOC += ' SOV_purge_spirit_%s_desc: "%s"\n' % (lvl, d)
for _g in ("ind", "mil", "ia", "int"):
    _n, _d = DATA["spirits"][_g]
    LOC += ' SOV_%s_dm: "%s"\n' % (_g, _n)
    LOC += ' SOV_%s_dm_desc: "%s"\n' % (_g, _d)
LOC += ' GER_sov_test_handicap: "Тяжёлое положение Германии (тест)"\n'
LOC += ' SOV_purge_escalation_tt: "%s"\n' % DATA["text"]["SOV_purge_escalation_tt"]
LOC += ' SOV_propaganda_extra: "%s"\n' % DATA["text"]["SOV_propaganda_extra"]
LOC += ' SOV_resources_prospect: "%s"\n' % DATA["text"]["SOV_resources_prospect"]
for pid, _, _, _, _ in PROP_CAMPAIGNS:
    LOC += ' SOV_prop_%s: "%s"\n' % (pid, DATA["campaigns"][pid])
for rid, _, _, _ in RES_DEC:
    LOC += ' SOV_prospect_%s: "%s"\n' % (rid, DATA["resources"][rid])

def patch_propaganda_gates(text):
    pat = re.compile(r'\t*custom_trigger_tooltip\s*=\s*\{\s*tooltip\s*=\s*SOV_propaganda_campaigns_taken_\w+_tt\s*check_variable\s*=\s*\{[^}]*\}\s*\}\s*\n', re.S)
    return pat.sub("", text)

def patch_purge_focus(text, focus_id):
    i = text.find("id = " + focus_id)
    if i < 0:
        raise RuntimeError("focus not found: " + focus_id)
    o, c = block_span(text, i)
    blk = text[o:c + 1]
    blk = blk.replace("SOV_paranoia_high_increase_effect = yes", "SOV_purge_escalate_effect = yes")
    blk = blk.replace("custom_effect_tooltip = SOV_will_trigger_a_great_purge_tt",
                      "custom_effect_tooltip = SOV_purge_escalation_tt")
    if "SOV_purge_escalate_effect" not in blk:
        blk = blk.replace("completion_reward = {",
                          "completion_reward = {\n\t\t\tSOV_purge_escalate_effect = yes", 1)
    return text[:o] + blk + text[c + 1:]

def patch_behead(text):
    i = text.find("id = SOV_behead_the_snake")
    o, c = block_span(text, i)
    blk = text[o:c + 1].replace("SOV_paranoia_high_decrease_effect = yes", "SOV_purge_stop_effect = yes")
    # без агентуры в фокусах
    blk = re.sub(r'(?m)^\s*operative_slot\s*=\s*\d+\s*\n', '', blk)
    blk = re.sub(r'(?m)^\s*(add_to_variable|set_variable) = \{ SOV_the_politburo_operative_slot\s*=\s*1 \}\s*\n', '', blk)
    # вырезаем создание оперативника (Рамона Меркадера) и весь блок La Resistance
    cr = blk.find("completion_reward = {")
    i = blk.find("if = {", cr)
    if i > 0:
        bo = blk.index("{", i)
        bc = find_block(blk, bo)
        tail = blk[bc + 1:]
        j = tail.find("else = {")
        if j >= 0 and tail[:j].strip() == "":
            eo = tail.index("{", j)
            ec = find_block(tail, eo)
            tail = tail[ec + 1:]
        head = blk[:i]
        if "SOV_purge_stop_effect" not in head:
            head += "\t\t\tSOV_purge_stop_effect = yes\n"
        blk = head + tail
    blk = re.sub(r"(SOV_purge_stop_effect = yes)(\s*SOV_purge_stop_effect = yes)+",
                  r"\1", blk)
    return text[:o] + blk + text[c + 1:]

def patch_agitprop(text):
    i = text.find("id = SOV_expand_the_agitprop")
    o, c = block_span(text, i)
    blk = text[o:c + 1]
    if "add_stability = 0.05" not in blk:
        blk = blk.replace("add_political_power = 25", "add_political_power = 25\n\t\t\tadd_stability = 0.05", 1)
    return text[:o] + blk + text[c + 1:]

def inject_into_tree(text, focus_text):
    idx = text.find("id = soviet_focus")
    if idx < 0:
        raise RuntimeError("soviet_focus tree not found")
    tree_start = text.rfind("focus_tree", 0, idx)
    o = text.index("{", tree_start)
    c = find_block(text, o)
    return text[:c] + "\n" + focus_text + "\n" + text[c:]

def build_soviet_file():
    src = rd(os.path.join(GAME, "common", "national_focus", "soviet.txt"))
    src = patch_propaganda_gates(src)
    for fid in ("SOV_the_zinovyevite_terrorist_center", "SOV_the_anti_soviet_trotskyist_center",
                "SOV_the_military_conspiracy", "SOV_the_bloc_of_rights_and_trotskyites"):
        src = patch_purge_focus(src, fid)
    src = patch_behead(src)
    src = patch_agitprop(src)
    src = src.replace("add_to_variable = { SOV_fyp_consumer_goods_factor = 0.10 }",
                      "add_to_variable = { SOV_fyp_consumer_goods_factor = 0.07 }")
    src = src.replace("add_to_variable = { SOV_fyp_production_factory_max_efficiency_factor = 0.05 }",
                      "add_to_variable = { SOV_fyp_production_factory_max_efficiency_factor = 0.08 }")
    src = inject_into_tree(src, FOCUS_TEXT)
    return src

def build_triggers():
    p = os.path.join(GAME, "common", "scripted_triggers", "SOV_scripted_triggers.txt")
    src = rd(p)
    src = src.replace("""SOV_fourth_five_year_plan_available = {
\tcustom_trigger_tooltip = {
\t\ttooltip = SOV_fourth_five_year_plan_available_tt
\t\thas_country_flag = SOV_fourth_five_year_plan_available_flag
\t}
}""", """SOV_fourth_five_year_plan_available = {
\tcustom_trigger_tooltip = {
\t\ttooltip = SOV_fourth_five_year_plan_available_tt
\t\tOR = {
\t\t\thas_country_flag = SOV_fourth_five_year_plan_available_flag
\t\t\thas_completed_focus = SOV_third_five_year_plan
\t\t}
\t}
}""")
    src = src.replace("""SOV_third_five_year_plan_available = {
\tcustom_trigger_tooltip = {
\t\ttooltip = SOV_third_five_year_plan_available_tt
\t\tNOT = { has_country_flag = SOV_third_five_year_plan_locked_flag }
\t}
}""", """SOV_third_five_year_plan_available = {
\tcustom_trigger_tooltip = {
\t\ttooltip = SOV_third_five_year_plan_available_tt
\t\talways = yes
\t}
}""")
    return src

def build_history():
    p = os.path.join(GAME, "history", "countries", "SOV - Soviet union.txt")
    src = rd(p)
    init = ["# --- sov_stalin_expanded: Р С—Р В°РЎР‚Р В°Р Р…Р С•Р в„–РЎРЏ Р С•РЎвЂљР С”Р В»РЎР‹РЎвЂЎР ВµР Р…Р В° ---",
            "set_variable = { SOV_purge_level = 0 }"]
    init.append("add_dynamic_modifier = { modifier = SOV_ia_dm }")
    for _g in ("ind", "mil", "ia", "int"):
        for _k in GROUP_KEYS[_g]:
            init.append("set_variable = { SOV_%s_%s = 0 }" % (_g, _k))
    init.append("")
    init.append("1941.2.1 = {")
    init.append("\tremove_ideas = SOV_purge_spirit_1")
    init.append("\tremove_ideas = SOV_purge_spirit_2")
    init.append("\tremove_ideas = SOV_purge_spirit_3")
    init.append("\tset_variable = { SOV_purge_level = 0 }")
    init.append("}")
    src = re.sub(r'country_event = \{ id = NSB_soviet_paranoia_system_events\.01[^\n]*\}',
                 "\n".join(init), src, count=1)
    return src

BUFF_LINES = [
    "industrial_capacity_factory = 0.10",
    "war_support_factor = 0.10",
    "stability_factor = 0.05",
    "consumer_goods_factor = -0.05",
]


def buff_campaigns(src):
    start = src.find("SOV_propaganda_campaigns = {")
    if start < 0:
        return src
    o = src.index("{", start)
    d = 0
    i = o
    ins = False
    while i < len(src):
        ch = src[i]
        if ins:
            if ch == '"': ins = False
        elif ch == '"': ins = True
        elif ch == "#":
            j = src.find("\n", i)
            i = len(src) if j < 0 else j
            continue
        elif ch == "{": d += 1
        elif ch == "}":
            d -= 1
            if d == 0: break
        i += 1
    head, body, tail = src[:o], src[o:i + 1], src[i + 1:]
    out = []
    for line in body.split("\n"):
        out.append(line)
        if line == "\t\tmodifier = {":
            for b in BUFF_LINES:
                out.append("\t\t" + b)
    return head + "\n".join(out) + tail


def build_categories():
    p = os.path.join(GAME, "common", "decisions", "categories", "SOV_decision_categories.txt")
    src = rd(p)
    src = src.replace("has_completed_focus = SOV_expand_the_agitprop", "always = yes")
    src = buff_campaigns(src)
    src = buff_resources(src)
    return src

def buff_resources(src):
    start = src.find("prospect_for_resources = {")
    if start < 0:
        return src
    o = src.index("{", start)
    d = 0
    i = o
    ins = False
    while i < len(src):
        ch = src[i]
        if ins:
            if ch == '"': ins = False
        elif ch == '"': ins = True
        elif ch == "#":
            j = src.find("\n", i)
            i = len(src) if j < 0 else j
            continue
        elif ch == "{": d += 1
        elif ch == "}":
            d -= 1
            if d == 0: break
        i += 1
    head, body, tail = src[:o], src[o:i + 1], src[i + 1:]

    def bump(m):
        amt = min(int(m.group(2)) * 3, 15)
        return "add_resource = {\n\t\t\ttype = %s\n\t\t\tamount = %d\n\t\t}" % (m.group(1), amt)

    body = re.sub(r"add_resource = \{\s*type = (\w+)\s*amount = (\d+)\s*\}", bump, body)
    return head + body + tail


def build_decisions():
    p = os.path.join(GAME, "common", "decisions", "SOV.txt")
    src = rd(p)
    src = src.replace("has_completed_focus = SOV_expand_the_agitprop", "always = yes")
    src = buff_campaigns(src)
    src = buff_resources(src)
    return src

ON_ACTIONS = """on_actions = {
\ton_startup = {
\t\teffect = {
\t\t\tGER = { add_ideas = GER_sov_test_handicap }
\t\t\tSOV = {
\t\t\t\tset_variable = { SOV_poster_left_icon_frame = SOV_propaganda_empty_slot_index }
\t\t\t\tset_variable = { SOV_poster_center_icon_frame = SOV_propaganda_empty_slot_index }
\t\t\t\tset_variable = { SOV_poster_right_icon_frame = SOV_propaganda_empty_slot_index }
\t\t\t}
\t\t}
\t}
\ton_war_relation_added = {
\t\teffect = {
\t\t\tif = {
\t\t\t\tlimit = {
\t\t\t\t\tOR = {
\t\t\t\t\t\toriginal_tag = SOV
\t\t\t\t\t\tFROM = { original_tag = SOV }
\t\t\t\t\t}
\t\t\t\t}
\t\t\t\tSOV = { clr_country_flag = SOV_third_five_year_plan_locked_flag }
\t\t\t}
\t\t}
\t}
\ton_monthly = {
\t\teffect = {
\t\t\tif = {
\t\t\t\tlimit = {
\t\t\t\t\toriginal_tag = SOV
\t\t\t\t\tdate > 1941.2.1
\t\t\t\t}
\t\t\t\tif = { limit = { has_idea = SOV_purge_spirit_1 } remove_ideas = SOV_purge_spirit_1 }
\t\t\t\tif = { limit = { has_idea = SOV_purge_spirit_2 } remove_ideas = SOV_purge_spirit_2 }
\t\t\t\tif = { limit = { has_idea = SOV_purge_spirit_3 } remove_ideas = SOV_purge_spirit_3 }
\t\t\t}
\t\t}
\t}
}
"""

DESCRIPTOR = """version="1.0"
tags={ "Alternative History" "Gameplay" "Balance" }
name="<MODNAME>"
supported_version="1.19.*"
path="mod/sov_stalin_expanded"
"""

def main():
    if not os.path.isdir(MODROOT):
        os.makedirs(MODROOT)
    soviet = build_soviet_file()
    wr(os.path.join(MODROOT, "common", "national_focus", "soviet.txt"), soviet)
    wr(os.path.join(MODROOT, "common", "scripted_triggers", "SOV_scripted_triggers.txt"), build_triggers())
    wr(os.path.join(MODROOT, "history", "countries", "SOV - Soviet union.txt"), build_history())
    wr(os.path.join(MODROOT, "common", "decisions", "categories", "SOV_decision_categories.txt"), build_categories())
    wr(os.path.join(MODROOT, "common", "decisions", "SOV.txt"), build_decisions())
    wr(os.path.join(MODROOT, "common", "dynamic_modifiers", "zz_sov_stalin.txt"), DM_TEXT)
    wr(os.path.join(MODROOT, "common", "ideas", "zz_sov_purge.txt"), IDEAS_TEXT)
    wr(os.path.join(MODROOT, "common", "scripted_effects", "zz_sov_effects.txt"), EFFECTS_TEXT)
    wr(os.path.join(MODROOT, "common", "on_actions", "zz_sov_on_actions.txt"), ON_ACTIONS)
    wr(os.path.join(MODROOT, "localisation", "russian", "zz_sov_stalin_l_russian.yml"), LOC, bom=True)
    desc = DESCRIPTOR.replace("<MODNAME>", DATA["mod_name"])
    wr(os.path.join(MODROOT, "descriptor.mod"), desc)
    wr(os.path.join(MODDIR, "sov_stalin_expanded.mod"), desc)
    print("built:", MODROOT)

if __name__ == "__main__":
    main()


