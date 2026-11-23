# -*- coding: utf-8 -*-
"""Стройка и ремонт — калькуляторы (Kivy, APK).
Версия 9 (диагностическая): запуск целиком обёрнут в защиту. Если приложение
падает даже до главного экрана (сбой импорта или до окна), ошибка показывается
на отдельном экране; если и это невозможно — отправляется через системное меню
«Поделиться» или сохраняется в Download/repaircalc_crash.txt.
Пришли текст ошибки Алисе. В остальном — версия 8 без изменений:
13 калькуляторов, 5 тем, запоминание ввода, «Поделиться»."""

import traceback

DEBUG_TB = None


def _crash_toast(msg):
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Toast = autoclass("android.widget.Toast")
        Toast.makeText(PythonActivity.mActivity, msg, Toast.LENGTH_LONG).show()
        return True
    except Exception:
        return False


def _crash_share(tb):
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        intent = Intent()
        intent.setAction(Intent.ACTION_SEND)
        intent.setType("text/plain")
        intent.putExtra(Intent.EXTRA_TEXT, "ОШИБКА ЗАПУСКА «СТРОЙКА И РЕМОНТ»:\n\n" + tb)
        PythonActivity.mActivity.startActivity(
            Intent.createChooser(intent, "Отправить ошибку Алисе"))
        return True
    except Exception:
        return False


def _crash_screen(tb):
    try:
        from kivy.app import App
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.label import Label
        from kivy.metrics import dp

        class CrashApp(App):
            title = "Ошибка запуска (диагностика)"

            def build(self):
                root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
                head = Label(text="Ошибка запуска — сделай скриншот и пришли Алисе",
                             font_size="14sp", bold=True,
                             color=(0.78, 0.27, 0.21, 1),
                             size_hint_y=None, height=dp(44),
                             halign="center", valign="middle")
                head.bind(size=lambda inst, s: setattr(inst, "text_size", s))
                root.add_widget(head)
                scroll = ScrollView(do_scroll_x=False)
                lbl = Label(text=tb, font_size="11sp", color=(0.1, 0.1, 0.1, 1),
                            halign="left", valign="top", size_hint_y=None)
                lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
                lbl.bind(texture_size=lbl.setter("size"))
                scroll.add_widget(lbl)
                root.add_widget(scroll)
                return root

        CrashApp().run()
        return True
    except Exception:
        return False


def _crash_file(tb):
    try:
        with open("/sdcard/Download/repaircalc_crash.txt", "w", encoding="utf-8") as f:
            f.write(tb)
        return True
    except Exception:
        return False


try:
    # -*- coding: utf-8 -*-
    """Стройка и ремонт — калькуляторы (Kivy, APK).
    Версия 8: 13 калькуляторов + эргономика + починенная отправка + выбор темы
    (Синяя, Оранжевая, Зелёная, Фиолетовая, Тёмная) на главном экране; выбор запоминается.
    числовая клавиатура, кнопки закреплены внизу, результат в общей прокрутке,
    кнопка «Сбросить», системная «Назад» возвращает на главный экран,
    клавиатура закрывается тапом мимо поля."""

    import json
    import os

    from kivy.app import App
    from kivy.uix.screenmanager import ScreenManager, Screen
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.label import Label
    from kivy.uix.textinput import TextInput
    from kivy.uix.spinner import Spinner
    from kivy.uix.button import Button
    from kivy.metrics import dp
    from kivy.graphics import Color, RoundedRectangle

    GOOD = (0.16, 0.55, 0.32, 1)
    DANGER = (0.78, 0.27, 0.21, 1)

    # --- темы оформления ---
    THEMES = {
        "Синяя": dict(
            accent=(0.10, 0.46, 0.82, 1), accent_dark=(0.05, 0.33, 0.62, 1),
            accent_soft=(0.89, 0.94, 0.99, 1),
            soft=[(0.90, 0.94, 0.99, 1), (0.90, 0.97, 0.92, 1), (0.93, 0.92, 0.99, 1),
                  (0.99, 0.96, 0.88, 1), (0.88, 0.96, 0.97, 1), (0.93, 0.95, 0.97, 1)],
            text=(0.11, 0.14, 0.19, 1), muted=(0.42, 0.45, 0.5, 1),
            card=(1, 1, 1, 1), grey=(0.90, 0.91, 0.93, 1), bg=(0.96, 0.95, 0.94, 1),
        ),
        "Оранжевая": dict(
            accent=(0.88, 0.48, 0.22, 1), accent_dark=(0.72, 0.38, 0.16, 1),
            accent_soft=(0.99, 0.93, 0.89, 1),
            soft=[(0.99, 0.93, 0.89, 1), (0.93, 0.97, 0.94, 1), (0.93, 0.95, 0.99, 1),
                  (0.99, 0.96, 0.93, 1), (0.96, 0.94, 0.99, 1), (0.98, 0.97, 0.91, 1)],
            text=(0.11, 0.14, 0.19, 1), muted=(0.42, 0.45, 0.5, 1),
            card=(1, 1, 1, 1), grey=(0.90, 0.91, 0.93, 1), bg=(0.97, 0.95, 0.93, 1),
        ),
        "Зелёная": dict(
            accent=(0.18, 0.49, 0.20, 1), accent_dark=(0.10, 0.35, 0.13, 1),
            accent_soft=(0.91, 0.96, 0.91, 1),
            soft=[(0.91, 0.96, 0.91, 1), (0.90, 0.94, 0.99, 1), (0.93, 0.92, 0.99, 1),
                  (0.99, 0.96, 0.88, 1), (0.88, 0.96, 0.97, 1), (0.93, 0.97, 0.93, 1)],
            text=(0.11, 0.14, 0.19, 1), muted=(0.42, 0.45, 0.5, 1),
            card=(1, 1, 1, 1), grey=(0.90, 0.91, 0.93, 1), bg=(0.95, 0.97, 0.94, 1),
        ),
        "Фиолетовая": dict(
            accent=(0.42, 0.11, 0.60, 1), accent_dark=(0.29, 0.08, 0.55, 1),
            accent_soft=(0.95, 0.90, 0.96, 1),
            soft=[(0.95, 0.90, 0.96, 1), (0.93, 0.92, 0.99, 1), (0.90, 0.94, 0.99, 1),
                  (0.99, 0.93, 0.89, 1), (0.88, 0.96, 0.97, 1), (0.96, 0.94, 0.99, 1)],
            text=(0.11, 0.14, 0.19, 1), muted=(0.42, 0.45, 0.5, 1),
            card=(1, 1, 1, 1), grey=(0.90, 0.91, 0.93, 1), bg=(0.96, 0.95, 0.97, 1),
        ),
        "Тёмная": dict(
            accent=(0.39, 0.71, 0.96, 1), accent_dark=(0.55, 0.78, 0.97, 1),
            accent_soft=(0.17, 0.21, 0.27, 1),
            soft=[(0.17, 0.21, 0.28, 1), (0.16, 0.23, 0.24, 1), (0.20, 0.18, 0.26, 1),
                  (0.24, 0.22, 0.18, 1), (0.16, 0.22, 0.26, 1), (0.20, 0.22, 0.25, 1)],
            text=(0.92, 0.93, 0.95, 1), muted=(0.66, 0.70, 0.75, 1),
            card=(0.14, 0.17, 0.22, 1), grey=(0.26, 0.29, 0.34, 1), bg=(0.09, 0.11, 0.14, 1),
        ),
    }
    DEFAULT_THEME = "Синяя"
    THEME = dict(THEMES[DEFAULT_THEME])


    def apply_theme(name):
        """Переключает активную палитру (всё пересобирается сразу)."""
        THEME.clear()
        THEME.update(THEMES.get(name, THEMES[DEFAULT_THEME]))

    SECTIONS = [
        ("📐 Сначала измерьте", [
            ("areas", "📐", "Площади", "пол, стены, объём"),
        ]),
        ("📌 Стены", [
            ("plaster", "🖌", "Штукатурка", "стены и мешки"),
            ("wallpaper", "🖼", "Обои", "полосы и рулоны"),
            ("paint", "🎨", "Краска", "литры и банки"),
            ("gkl", "🔲", "Гипсокартон", "листы и профиль"),
            ("bricks", "🧱", "Кирпич и блоки", "штуки и раствор"),
        ]),
        ("▦ Полы", [
            ("screed", "🔨", "Стяжка", "смесь и мешки"),
            ("laminate", "🌲", "Ламинат", "доски и упаковки"),
            ("tile", "🔷", "Плитка", "коробки, клей, затирка"),
            ("plinth", "📏", "Плинтус", "планки и углы"),
        ]),
        ("⚙ Дом и комфорт", [
            ("concrete", "🏗", "Бетон", "цемент, песок, щебень"),
            ("insulation", "❄", "Утеплитель", "плиты и упаковки"),
            ("heat", "🔥", "Отопление", "кВт и секции"),
        ]),
    ]

    ALL_TILES = [t for _title, items in SECTIONS for t in items]
    N_CALCS = len(ALL_TILES)


    def fmt(x, d=2):
        return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")


    def ceil_up(x):
        n = int(x)
        return n if abs(x - n) < 1e-9 else n + 1


    def parse_float(s):
        s = (s or "").strip().replace(",", ".")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            raise ValueError("Проверьте числа: где-то пусто или не число.")


    def num(v, default=None):
        """Число с запасным значением: если поле пусто — default."""
        return default if v is None else v


    def float_filter(text, from_clipboard):
        """Пропускает цифры, точку, запятую и минус; вставку из буфера чистит."""
        allowed = "".join(ch for ch in text if ch in "0123456789.,-+")
        if from_clipboard:
            return allowed
        return True if allowed else ""


    # ---------- расчёты ----------

    def c_areas(v):
        w, l, h = v["w"], v["l"], v["h"]
        floor = w * l
        perim = 2 * (w + l)
        walls = perim * h
        opening = 0
        if v.get("doors"):
            opening += v["doors"] * (v["door_w"] or 0) * (v["door_h"] or 0)
        if v.get("wins"):
            opening += v["wins"] * (v["win_w"] or 0) * (v["win_h"] or 0)
        walls_net = max(0, walls - opening)
        return (
            "Пол: " + fmt(floor) + " м²\n"
            "Потолок: " + fmt(floor) + " м²\n"
            "Периметр: " + fmt(perim) + " м\n"
            "Стены целиком: " + fmt(walls) + " м²\n"
            "Стены без проёмов: " + fmt(walls_net) + " м² — под обои и краску\n"
            "Объём комнаты: " + fmt(floor * h) + " м³"
        )


    def c_screed(v):
        rates = {"ЦПС (цементно-песчаная)": 1.8, "Наливной пол": 1.5, "Керамзитобетон": 1.2}
        kind = v["type"]
        rate = v["custom"] if kind == "Своя цифра" else rates[kind]
        if not rate:
            raise ValueError("Выберите смесь или впишите свой расход.")
        kg = v["area"] * v["thick"] * rate
        bag = num(v["bag"], 40)
        if bag <= 0:
            raise ValueError("Вес мешка должен быть больше нуля.")
        return (
            "Мешков по " + fmt(bag, 0) + " кг: " + str(ceil_up(kg / bag)) + " шт\n"
            "Нужно смеси: " + fmt(kg, 0) + " кг (" + fmt(kg / 1000, 2) + " т)\n"
            "Объём слоя: " + fmt(v["area"] * v["thick"] / 1000) + " м³\n\n"
            "Мин. толщина: ЦПС от 30 мм; наливной пол — по инструкции на мешке."
        )


    def c_plaster(v):
        rates = {"Гипсовая (Ротбанд и т.п.)": 0.9, "Цементная": 1.7, "Шпаклёвка финишная": 1.2}
        kind = v["type"]
        rate = v["custom"] if kind == "Своя цифра" else rates[kind]
        if not rate:
            raise ValueError("Выберите смесь или впишите свой расход.")
        kg = v["area"] * v["thick"] * rate
        bag = num(v["bag"], 30)
        if bag <= 0:
            raise ValueError("Вес мешка должен быть больше нуля.")
        return (
            "Мешков по " + fmt(bag, 0) + " кг: " + str(ceil_up(kg / bag)) + " шт\n"
            "Нужно смеси: " + fmt(kg, 0) + " кг\n"
            "На каждый +1 мм слоя: ещё " + fmt(v["area"] * rate, 0) + " кг\n\n"
            "Кривые стены: закладывайте ещё 10–15% сверху."
        )


    def c_paint(v):
        rate = num(v["rate"], 0.12)
        coats = num(v["coats"], 2)
        liters = v["area"] * coats * rate
        can = num(v["can"], 2.5)
        if can <= 0:
            raise ValueError("Объём банки должен быть больше нуля.")
        return (
            "Банок по " + fmt(can, 1) + " л: " + str(ceil_up(liters / can)) + " шт\n"
            "Нужно краски: " + fmt(liters) + " л\n"
            "На один слой: " + fmt(v["area"] * rate) + " л\n\n"
            "Обычный расход водоэмульсионки — 0,1–0,15 л/м² на слой."
        )


    def c_wallpaper(v):
        perim = v["perim"]
        h = num(v["height"], 2.7)
        rw = num(v["rw"], 0.53)
        rl = num(v["rl"], 10.05)
        margin = num(v["margin"], 10) / 100
        strip_len = h + margin
        strips = ceil_up(perim / rw)
        per_roll = int(rl // strip_len)
        if per_roll <= 0:
            return "Рулон короче одной полосы — нужен более длинный рулон."
        rolls = ceil_up(strips / per_roll)
        return (
            "Рулонов нужно: " + str(rolls) + "\n"
            "Полос на комнату: " + str(strips) + " (по " + fmt(strip_len, 1) + " м)\n"
            "Полос из рулона: " + str(per_roll) + "\n"
            "Всего полотна: " + fmt(strips * strip_len) + " м\n\n"
            "Проёмы не вычитаем: остаток уходит на откосы и подгонку."
        )


    def c_heat(v):
        area = v["area"]
        h = num(v["height"], 2.7)
        coef = {"Хорошее": 0.85, "Среднее": 1.0, "Слабое": 1.25}[v["insul"]]
        watts = area * 100 * (h / 2.7) * coef
        section = num(v["section"], 170)
        if section <= 0:
            raise ValueError("Мощность секции должна быть больше нуля.")
        return (
            "Мощность: " + fmt(watts, 0) + " Вт = " + fmt(watts / 1000, 1) + " кВт\n"
            "Секций по " + fmt(section, 0) + " Вт: " + str(ceil_up(watts / section)) + " шт\n"
            "Это " + fmt(watts / area, 0) + " Вт на каждый м²\n\n"
            "База — 100 Вт/м² при потолке 2,7 м."
        )


    def c_concrete(v):
        grades = {
            "М200 (дорожки, отмостка)": (265, 860, 1050, 180, "1 : 2,8 : 4,8"),
            "М250 (фундамент, столбы)": (320, 800, 1050, 175, "1 : 2,5 : 4,3"),
            "М300 (плита, перекрытие)": (380, 730, 1080, 170, "1 : 1,9 : 2,8"),
        }
        cem_r, sand_r, grav_r, water_r, prop = grades[v["grade"]]
        bag = num(v["bag"], 50)
        if bag <= 0:
            raise ValueError("Вес мешка должен быть больше нуля.")
        vol = v["w"] * v["l"] * v["thick"] / 100
        vol_res = vol * 1.1
        cem = vol_res * cem_r
        mark = v["grade"].split(" ")[0]
        return (
            "Мешков по " + fmt(bag, 0) + " кг: " + str(ceil_up(cem / bag)) + " шт (" + fmt(cem, 0) + " кг)\n"
            "Песка: " + fmt(vol_res * sand_r, 0) + " кг (" + fmt(vol_res * sand_r / 1500, 2) + " м³)\n"
            "Щебня: " + fmt(vol_res * grav_r, 0) + " кг\n"
            "Воды: " + fmt(vol_res * water_r, 0) + " л\n"
            "Бетона с запасом 10%: " + fmt(vol_res, 2) + " м³\n\n"
            + mark + ": пропорция по массе цемент : песок : щебень ≈ " + prop + "."
        )


    def c_tile(v):
        area = v["area"]
        tw = v["tw"]
        th = v["th"]
        piece = tw * th / 10000
        if piece <= 0:
            raise ValueError("Размер плитки должен быть больше нуля.")
        reserve = num(v["reserve"], 10)
        box = num(v["box"], 11)
        if box <= 0:
            raise ValueError("Плиток в коробке должно быть больше нуля.")
        pieces = ceil_up(area * (1 + reserve / 100) / piece)
        boxes = ceil_up(pieces / box)
        glue_kg = area * (1 + reserve / 100) * num(v["glue"], 5)
        bag = num(v["bag"], 25)
        if bag <= 0:
            raise ValueError("Вес мешка клея должен быть больше нуля.")
        bags = ceil_up(glue_kg / bag)
        w_m, h_m = tw / 100.0, th / 100.0
        joint = num(v["joint"], 3) / 1000.0
        depth = num(v["depth"], 8) / 1000.0
        grout_m2 = (w_m + h_m) / (w_m * h_m) * joint * depth * 1600
        grout_kg = area * (1 + reserve / 100) * grout_m2
        return (
            "Плиток: " + str(pieces) + " шт (" + str(boxes) + " коробк. по " + fmt(box, 0) + ")\n"
            "Площадь с запасом: " + fmt(area * (1 + reserve / 100)) + " м²\n"
            "Клея: " + fmt(glue_kg, 0) + " кг — " + str(bags) + " мешк. по " + fmt(bag, 0) + " кг\n"
            "Затирки: " + fmt(grout_kg, 1) + " кг\n\n"
            "Плитка " + fmt(tw, 0) + "×" + fmt(th, 0) + " см покрывает " + fmt(piece, 3) + " м²."
        )


    def c_laminate(v):
        w, l = v["w"], v["l"]
        area = w * l
        pw = num(v["pw"], 128)
        pl = num(v["pl"], 19)
        piece = pw * pl / 10000.0
        if piece <= 0:
            raise ValueError("Размер доски должен быть больше нуля.")
        reserve = num(v["reserve"], 7)
        pack = num(v["pack"], 8)
        if pack <= 0:
            raise ValueError("Досок в упаковке должно быть больше нуля.")
        pieces = ceil_up(area * (1 + reserve / 100) / piece)
        packs = ceil_up(pieces / pack)
        pod = num(v["pod"], 15)
        if pod <= 0:
            raise ValueError("Площадь подложки в рулоне должна быть больше нуля.")
        rolls = ceil_up(area * (1 + reserve / 100) / pod)
        return (
            "Площадь: " + fmt(area) + " м² (с запасом " + fmt(area * (1 + reserve / 100)) + " м²)\n"
            "Досок: " + str(pieces) + " шт — " + str(packs) + " упаковк. по " + fmt(pack, 0) + "\n"
            "Подложки: " + str(rolls) + " рулон(ов)\n\n"
            "Кладите вдоль света из окна, запас 7–10% на подрезку."
        )


    def c_gkl(v):
        area = v["area"]
        sh_l = num(v["sh_l"], 250)
        sh_w = num(v["sh_w"], 120)
        piece = sh_l * sh_w / 10000.0
        if piece <= 0:
            raise ValueError("Размер листа должен быть больше нуля.")
        reserve = num(v["reserve"], 10)
        sheets = ceil_up(area * (1 + reserve / 100) / piece)
        covered = area * (1 + reserve / 100)
        cd = ceil_up(covered * 1.7 / 3)  # стойки/несущие шагом 60 см, профили по 3 м
        perim = v["perim"]
        if perim:
            ud = ceil_up(perim / 3)
            ud_text = "Направляющих UD/ПН: " + str(ud) + " шт по 3 м\n"
        else:
            ud_text = ""
        hangers = ceil_up(covered * 4)
        screws = ceil_up(covered * 30)
        return (
            "Листов: " + str(sheets) + " шт (" + fmt(sh_l / 100, 2) + "×" + fmt(sh_w / 100, 2) + " м)\n"
            "Профиля CD/ПС: " + str(cd) + " шт по 3 м\n"
            + ud_text +
            "Подвесов: " + str(hangers) + " шт\n"
            "Саморезов для ГКЛ: около " + str(screws) + " шт\n\n"
            "Профиль берите шагом 60 см, подвесы — по 4 на м²."
        )


    def c_insulation(v):
        area = v["area"]
        thick = num(v["thick"], 50)
        sw = num(v["sw"], 100)
        sh = num(v["sh"], 60)
        piece = sw * sh / 10000.0
        if piece <= 0:
            raise ValueError("Размер плиты должен быть больше нуля.")
        reserve = num(v["reserve"], 10)
        pack = num(v["pack"], 6)
        if pack <= 0:
            raise ValueError("Плит в упаковке должно быть больше нуля.")
        plates = ceil_up(area * (1 + reserve / 100) / piece)
        packs = ceil_up(plates / pack)
        vol = area * (1 + reserve / 100) * thick / 1000
        return (
            "Плит: " + str(plates) + " шт (" + fmt(sw / 100, 2) + "×" + fmt(sh / 100, 2) + " м)\n"
            "Упаковок: " + str(packs) + " по " + fmt(pack, 0) + " плит\n"
            "Объём утеплителя: " + fmt(vol, 2) + " м³ при толщине " + fmt(thick, 0) + " мм\n\n"
            "Плотность и состав упаковки у брендов различаются — сверьте с этикеткой."
        )


    def c_plinth(v):
        perim = v["perim"]
        doors = num(v["doors"], 0.9)
        need = max(0, perim - doors)
        pl_len = num(v["pl_len"], 2.5)
        if pl_len <= 0:
            raise ValueError("Длина планки должна быть больше нуля.")
        reserve = num(v["reserve"], 5)
        planks = ceil_up(need * (1 + reserve / 100) / pl_len)
        return (
            "Погонных метров: " + fmt(need) + " м\n"
            "Планок по " + fmt(pl_len, 1) + " м: " + str(planks) + " шт\n"
            "С запасом на углы: " + fmt(need * (1 + reserve / 100)) + " м\n\n"
            "Внешних и внутренних углов обычно 4 — берите заглушки и уголки по цвету."
        )


    def c_bricks(v):
        per = {
            "Одинарный кирпич 250×120×65": [51, 102, 153, 204],
            "Полуторный кирпич 250×120×88": [39, 78, 117, 156],
        }
        thicks = {
            "В полкирпича (12 см)": (0, 0.12),
            "В кирпич (25 см)": (1, 0.25),
            "В полтора кирпича (38 см)": (2, 0.38),
            "В два кирпича (51 см)": (3, 0.51),
        }
        blocks = {"Газоблок 600×250×200": 0.2, "Газоблок 600×250×300": 0.3, "Газоблок 600×250×400": 0.4}
        block_perm2 = 6.6
        area = max(0, v["w"] * v["h"] - (v["open"] or 0))
        reserve = num(v["reserve"], 5)
        if v["type"] in per:
            idx, t = thicks[v["th"]]
            perm2 = per[v["type"]][idx]
            vol = area * t
            bag = num(v["bag"], 50)
            if bag <= 0:
                raise ValueError("Вес мешка цемента должен быть больше нуля.")
            sol = vol * 0.22
            cbags = ceil_up(sol * 300 / bag)
            mortar = ("Раствора: " + fmt(sol, 2) + " м³ — около " + str(cbags)
                      + " мешк. цемента по " + fmt(bag, 0) + " кг и " + fmt(sol * 1200, 0) + " кг песка")
        else:
            t = blocks[v["type"]]
            perm2 = block_perm2
            vol = area * t
            glue = ceil_up(vol * 30 / 25)
            mortar = "Клея для газобетона: " + str(glue) + " мешк. по 25 кг (≈30 кг на м³)"
        plain = ceil_up(area * perm2)
        pieces = ceil_up(area * perm2 * (1 + reserve / 100))
        name = v["type"].split(" ")[0]
        return (
            "Штук с запасом: " + str(pieces) + " (без запаса " + str(plain) + ")\n"
            "На каждый м²: " + fmt(perm2, 1) + " шт\n"
            "Кладки без проёмов: " + fmt(area) + " м², объём: " + fmt(vol, 2) + " м³\n"
            + mortar + "\n\n"
            + name + " — берите палитрами, продавцы округлят сами."
        )


    SCREENS = [
        {
            "id": "areas", "title": "Площади комнаты",
            "req": ["w", "l", "h"],
            "fields": [
                ("w", "Ширина, м", "num", "4"),
                ("l", "Длина, м", "num", "5"),
                ("h", "Высота, м", "num", "2.7"),
                ("doors", "Дверей, шт", "num", "1"),
                ("door_w", "Ширина двери, м", "num", "0.9"),
                ("door_h", "Высота двери, м", "num", "2"),
                ("wins", "Окон, шт", "num", "1"),
                ("win_w", "Ширина окна, м", "num", "1.5"),
                ("win_h", "Высота окна, м", "num", "1.5"),
            ],
            "compute": c_areas,
        },
        {
            "id": "plaster", "title": "Штукатурка",
            "req": ["area"],
            "fields": [
                ("area", "Площадь стен, м²", "num", ""),
                ("thick", "Толщина слоя, мм", "num", "10"),
                ("type", "Смесь", "spin", "Гипсовая (Ротбанд и т.п.)",
                 ["Гипсовая (Ротбанд и т.п.)", "Цементная", "Шпаклёвка финишная", "Своя цифра"]),
                ("custom", "Свой расход, кг/м²/мм", "num", ""),
                ("bag", "Вес мешка, кг", "num", "30"),
            ],
            "compute": c_plaster,
        },
        {
            "id": "wallpaper", "title": "Обои",
            "req": ["perim"],
            "fields": [
                ("perim", "Периметр комнаты, м", "num", ""),
                ("height", "Высота стены, м", "num", "2.7"),
                ("rw", "Ширина рулона, м", "num", "0.53"),
                ("rl", "Длина рулона, м", "num", "10.05"),
                ("margin", "Запас на подрезку, см", "num", "10"),
            ],
            "compute": c_wallpaper,
        },
        {
            "id": "paint", "title": "Краска",
            "req": ["area"],
            "fields": [
                ("area", "Площадь, м²", "num", ""),
                ("coats", "Слоёв", "num", "2"),
                ("rate", "Расход, л/м² на слой", "num", "0.12"),
                ("can", "Объём банки, л", "num", "2.5"),
            ],
            "compute": c_paint,
        },
        {
            "id": "gkl", "title": "Гипсокартон",
            "req": ["area"],
            "fields": [
                ("area", "Площадь обшивки, м²", "num", ""),
                ("sh_l", "Длина листа, см", "num", "250"),
                ("sh_w", "Ширина листа, см", "num", "120"),
                ("perim", "Периметр (для направляющих), м", "num", ""),
                ("reserve", "Запас, %", "num", "10"),
            ],
            "compute": c_gkl,
        },
        {
            "id": "bricks", "title": "Кирпич и блоки",
            "req": ["w", "h"],
            "fields": [
                ("w", "Длина стены, м", "num", ""),
                ("h", "Высота стены, м", "num", ""),
                ("open", "Проёмы (двери, окна), м²", "num", ""),
                ("type", "Материал", "spin", "Одинарный кирпич 250×120×65",
                 ["Одинарный кирпич 250×120×65", "Полуторный кирпич 250×120×88",
                  "Газоблок 600×250×200", "Газоблок 600×250×300", "Газоблок 600×250×400"]),
                ("th", "Толщина кладки (для кирпича)", "spin", "В полкирпича (12 см)",
                 ["В полкирпича (12 см)", "В кирпич (25 см)", "В полтора кирпича (38 см)", "В два кирпича (51 см)"]),
                ("reserve", "Запас, %", "num", "5"),
                ("bag", "Вес мешка цемента, кг", "num", "50"),
            ],
            "compute": c_bricks,
        },
        {
            "id": "screed", "title": "Стяжка пола",
            "req": ["area", "thick"],
            "fields": [
                ("area", "Площадь пола, м²", "num", ""),
                ("thick", "Толщина слоя, мм", "num", ""),
