# -*- coding: utf-8 -*-
"""Стройка и ремонт — калькуляторы (Kivy, APK). Версия 2: карточки, запоминание ввода, «Поделиться»."""

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

ACCENT = (0.88, 0.48, 0.22, 1)
ACCENT_SOFT = (0.99, 0.93, 0.89, 1)
TEXT = (0.11, 0.14, 0.19, 1)
MUTED = (0.42, 0.45, 0.5, 1)
BG = (0.95, 0.95, 0.96, 1)
CARD = (1, 1, 1, 1)
GOOD = (0.16, 0.55, 0.32, 1)
DANGER = (0.78, 0.27, 0.21, 1)

TILES = [
    ("areas", "📐", "Площади", "пол, стены, объём"),
    ("screed", "🧱", "Стяжка", "смесь и мешки"),
    ("plaster", "🪣", "Штукатурка", "стены и мешки"),
    ("paint", "🎨", "Краска", "литры и банки"),
    ("wallpaper", "🖼", "Обои", "полосы и рулоны"),
    ("heat", "🔥", "Отопление", "кВт и секции"),
]


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
    bag = v["bag"] or 40
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
    bag = v["bag"] or 30
    return (
        "Мешков по " + fmt(bag, 0) + " кг: " + str(ceil_up(kg / bag)) + " шт\n"
        "Нужно смеси: " + fmt(kg, 0) + " кг\n"
        "На каждый +1 мм слоя: ещё " + fmt(v["area"] * rate, 0) + " кг\n\n"
        "Кривые стены: закладывайте ещё 10–15% сверху."
    )


def c_paint(v):
    rate = v["rate"] or 0.12
    coats = v["coats"] or 2
    liters = v["area"] * coats * rate
    can = v["can"] or 2.5
    return (
        "Банок по " + fmt(can, 1) + " л: " + str(ceil_up(liters / can)) + " шт\n"
        "Нужно краски: " + fmt(liters) + " л\n"
        "На один слой: " + fmt(v["area"] * rate) + " л\n\n"
        "Обычный расход водоэмульсионки — 0,1–0,15 л/м² на слой."
    )


def c_wallpaper(v):
    perim = v["perim"]
    h = v["height"] or 2.7
    rw = v["rw"] or 0.53
    rl = v["rl"] or 10.05
    margin = (v["margin"] or 10) / 100
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
    h = v["height"] or 2.7
    coef = {"Хорошее": 0.85, "Среднее": 1.0, "Слабое": 1.25}[v["insul"]]
    watts = area * 100 * (h / 2.7) * coef
    section = v["section"] or 170
    return (
        "Мощность: " + fmt(watts, 0) + " Вт = " + fmt(watts / 1000, 1) + " кВт\n"
        "Секций по " + fmt(section, 0) + " Вт: " + str(ceil_up(watts / section)) + " шт\n"
        "Это " + fmt(watts / area, 0) + " Вт на каждый м²\n\n"
        "База — 100 Вт/м² при потолке 2,7 м."
    )


SCREENS = [
    {
        "id": "areas", "title": "Площади комнаты",
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
        "id": "screed", "title": "Стяжка пола",
        "fields": [
            ("area", "Площадь пола, м²", "num", ""),
            ("thick", "Толщина слоя, мм", "num", ""),
            ("type", "Смесь", "spin", "ЦПС (цементно-песчаная)",
             ["ЦПС (цементно-песчаная)", "Наливной пол", "Керамзитобетон", "Своя цифра"]),
            ("custom", "Свой расход, кг/м²/мм", "num", ""),
            ("bag", "Вес мешка, кг", "num", "40"),
        ],
        "compute": c_screed,
    },
    {
        "id": "plaster", "title": "Штукатурка",
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
        "id": "paint", "title": "Краска",
        "fields": [
            ("area", "Площадь, м²", "num", ""),
            ("coats", "Слоёв", "num", "2"),
            ("rate", "Расход, л/м² на слой", "num", "0.12"),
            ("can", "Объём банки, л", "num", "2.5"),
        ],
        "compute": c_paint,
    },
    {
        "id": "wallpaper", "title": "Обои",
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
        "id": "heat", "title": "Отопление",
        "fields": [
            ("area", "Площадь, м²", "num", ""),
            ("height", "Высота потолка, м", "num", "2.7"),
            ("insul", "Утепление", "spin", "Среднее", ["Хорошее", "Среднее", "Слабое"]),
            ("section", "Мощность секции, Вт", "num", "170"),
        ],
        "compute": c_heat,
    },
]


class Panel(BoxLayout):
    """Карточка со скруглёнными углами."""

    def __init__(self, bg=CARD, radius=16, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*bg)
            self._rect = RoundedRectangle(radius=[dp(radius)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class Tile(Button):
    """Плоская цветная кнопка без стандартной текстуры."""

    def __init__(self, bg=ACCENT, radius=12, **kw):
        super().__init__(background_normal="", background_down="", **kw)
        with self.canvas.before:
            Color(*bg)
            self._rect = RoundedRectangle(radius=[dp(radius)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size


DEBUG_TB = None


def make_error_screen(tb):
    """Отладочный экран: показывает traceback прямо в приложении."""
    root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
    head = Label(text="Ошибка запуска (отладка)", font_size="16sp", bold=True,
                 color=DANGER, size_hint_y=None, height=dp(30),
                 halign="center", valign="middle")
    head.bind(size=lambda inst, s: setattr(inst, "text_size", s))
    root.add_widget(head)
    hint = Label(text="Сделайте скриншот этого текста и пришлите Алисе",
                 font_size="13sp", color=MUTED, size_hint_y=None, height=dp(24),
                 halign="center", valign="middle")
    hint.bind(size=lambda inst, s: setattr(inst, "text_size", s))
    root.add_widget(hint)
    scroll = ScrollView(do_scroll_x=False)
    lbl = Label(text=tb, font_size="11sp", color=(0.1, 0.1, 0.1, 1),
                halign="left", valign="top", size_hint_y=None)
    lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
    lbl.bind(texture_size=lbl.setter("size"))
    scroll.add_widget(lbl)
    root.add_widget(scroll)
    return root


class DebugApp(App):
    title = "Ошибка запуска"

    def build(self):
        return make_error_screen(DEBUG_TB)


def make_row(label_text, kind, default, options=None):
    box = Panel(radius=12, orientation="vertical", size_hint_y=None,
                height=dp(66), padding=[dp(10), dp(6), dp(10), dp(6)])
    lbl = Label(text=label_text, font_size="13sp", color=MUTED,
                size_hint_y=None, height=dp(20), halign="left", valign="middle")
    lbl.bind(size=lambda inst, s: setattr(inst, "text_size", s))
    box.add_widget(lbl)
    if kind == "spin":
        widget = Spinner(text=default, values=options, font_size="15sp",
                         size_hint_y=None, height=dp(34),
                         background_normal="", background_down="",
                         background_color=(0.93, 0.94, 0.96, 1))
    else:
        widget = TextInput(multiline=False, text=default, font_size="16sp",
                           size_hint_y=None, height=dp(34),
                           background_normal="", background_active="",
                           background_color=(0.93, 0.94, 0.96, 1),
                           foreground_color=TEXT,
                           input_filter="float" if kind == "num" else None,
                           padding=[dp(8), dp(6), dp(8), dp(4)])
    box.add_widget(widget)
    return box, widget


class RepairApp(App):
    title = "Стройка и ремонт"

    def build(self):
        try:
            return self._real_build()
        except Exception:
            import traceback
            global DEBUG_TB
            DEBUG_TB = traceback.format_exc()
            print("ОТЛАДКА: ошибка в build():\n" + DEBUG_TB)
            return self._error_screen(DEBUG_TB)

    def _error_screen(self, tb):
        return make_error_screen(tb)

    def _real_build(self):
        self.field_widgets = {}
        self.saved = self.load_state()
        sm = ScreenManager()
        sm.add_widget(self.home_screen())
        for cfg in SCREENS:
            sm.add_widget(self.calc_screen(cfg))
        return sm

    # --- сохранение ввода ---
    def _state_path(self):
        try:
            return os.path.join(self.user_data_dir, "repaircalc.json")
        except Exception:
            return None

    def load_state(self):
        path = self._state_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_state(self):
        path = self._state_path()
        if not path:
            return
        data = {}
        for sid, ws in self.field_widgets.items():
            data[sid] = {k: w.text for k, w in ws.items() if hasattr(w, "text")}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass

    def on_stop(self):
        self.save_state()

    def on_pause(self):
        self.save_state()
        return True

    # --- экраны ---
    def open_screen(self, cid):
        self.root.current = cid

    def home_screen(self):
        screen = Screen(name="home")
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))
        header = Panel(bg=ACCENT, radius=18, size_hint_y=None, height=dp(96),
                       padding=[dp(16), dp(10), dp(16), dp(10)])
        header.add_widget(Label(text="Стройка и ремонт", font_size="24sp", bold=True,
                                color=(1, 1, 1, 1), halign="left", valign="middle",
                                size_hint_y=None, height=dp(34)))
        header.add_widget(Label(text="6 калькуляторов материалов",
                                font_size="13sp", color=(1, 1, 1, 0.85),
                                halign="left", valign="top"))
        header.children[0].bind(size=lambda inst, s: setattr(inst, "text_size", s))
        root.add_widget(header)

        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(320))
        grid.bind(minimum_height=grid.setter("height"))
        for cid, icon, title, subtitle in TILES:
            card = Panel(radius=14, size_hint=(1, None), height=dp(96),
                         padding=[dp(10), dp(8), dp(10), dp(8)])
            card.add_widget(Label(text=icon, font_size="26sp", size_hint_y=None, height=dp(34)))
            card.add_widget(Label(text=title, font_size="16sp", bold=True, color=TEXT,
                                  halign="left", valign="middle",
                                  size_hint_y=None, height=dp(24)))
            card.add_widget(Label(text=subtitle, font_size="12sp", color=MUTED,
                                  halign="left", valign="top"))
            card.children[1].bind(size=lambda inst, s: setattr(inst, "text_size", s))
            card.bind(on_touch_down=self._card_tap(cid))
            grid.add_widget(card)
        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(grid)
        root.add_widget(scroll)

        root.add_widget(Label(
            text="Последние значения запоминаются сами.\nРасходы смесей — средние типовые.",
            font_size="12sp", color=MUTED, size_hint_y=None, height=dp(40),
            halign="center", valign="middle"))
        screen.add_widget(root)
        return screen

    def _card_tap(self, cid):
        def handler(instance, touch):
            if instance.collide_point(*touch.pos) and self.root:
                self.open_screen(cid)
        return handler

    def calc_screen(self, cfg):
        screen = Screen(name=cfg["id"])
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        header = Panel(bg=ACCENT, radius=16, size_hint_y=None, height=dp(54),
                       padding=[dp(6), dp(6), dp(12), dp(6)])
        header_row = BoxLayout(orientation="horizontal", spacing=dp(8))
        back = Tile(bg=(1, 1, 1, 0.25), radius=10, text="←", font_size="20sp",
                    bold=True, color=(1, 1, 1, 1), size_hint=(None, 1), width=dp(44))
        back.bind(on_release=lambda inst: self.open_screen("home"))
        header_row.add_widget(back)
        title = Label(text=cfg["title"], font_size="19sp", bold=True, color=(1, 1, 1, 1),
                      halign="left", valign="middle")
        title.bind(size=lambda inst, s: setattr(inst, "text_size", s))
        header_row.add_widget(title)
        header.add_widget(header_row)
        root.add_widget(header)

        scroll = ScrollView(do_scroll_x=False, bar_color=ACCENT)
        grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(8),
                          padding=[dp(2), dp(2), dp(2), dp(2)])
        grid.bind(minimum_height=grid.setter("height"))

        widgets = {}
        for f in cfg["fields"]:
            key, label, kind = f[0], f[1], f[2]
            default = f[3] if len(f) > 3 else ""
            options = f[4] if len(f) > 4 else None
            if cfg["id"] in self.saved and key in self.saved[cfg["id"]]:
                default = self.saved[cfg["id"]][key]
            row, widget = make_row(label, kind, default, options)
            widgets[key] = widget
            grid.add_widget(row)
        scroll.add_widget(grid)
        root.add_widget(scroll)

        result_panel = Panel(bg=ACCENT_SOFT, radius=14, orientation="vertical",
                             size_hint_y=None, height=dp(40), padding=[dp(12), dp(8), dp(12), dp(8)])
        result = Label(text="Нажмите «Рассчитать»", font_size="15sp", color=TEXT,
                       halign="left", valign="top")
        result.bind(size=lambda inst, s: setattr(inst, "text_size", s))
        result_panel.add_widget(result)

        btn_row = BoxLayout(orientation="horizontal", spacing=dp(8),
                            size_hint_y=None, height=dp(52))
        btn = Tile(text="Рассчитать", font_size="17sp", bold=True, color=(1, 1, 1, 1))
        btn.bind(on_release=lambda inst: self.do_calc(cfg, widgets, result, result_panel))
        share = Tile(text="Поделиться", font_size="15sp", color=ACCENT,
                     bg=(1, 1, 1, 1), size_hint_x=0.42)
        share.bind(on_release=lambda inst: self.share_result(result.text))
        btn_row.add_widget(btn)
        btn_row.add_widget(share)
        root.add_widget(result_panel)
        root.add_widget(btn_row)
        screen.add_widget(root)

        self.field_widgets[cfg["id"]] = widgets
        return screen

    def do_calc(self, cfg, widgets, result, result_panel):
        values = {}
        try:
            for f in cfg["fields"]:
                key, kind = f[0], f[2]
                if kind == "num":
                    values[key] = parse_float(widgets[key].text)
                else:
                    values[key] = widgets[key].text
            for key, label, kind in [(f[0], f[1], f[2]) for f in cfg["fields"]]:
                if kind == "num" and values[key] is None and key in ("w", "l", "h", "area", "thick", "perim"):
                    raise ValueError("Заполните поле: " + label)
            text = cfg["compute"](values)
            color = TEXT
        except ValueError as e:
            text, color = "⚠ " + str(e), DANGER
        except (ZeroDivisionError, KeyError, TypeError):
            text, color = "⚠ Проверьте введённые числа.", DANGER
        result.text = text
        result.color = color
        result_panel.height = dp(24) * (text.count("\n") + 2) + dp(16)
        self.save_state()

    def share_result(self, text):
        if not text or text.startswith("⚠") or text == "Нажмите «Рассчитать»":
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Str = autoclass("java.lang.String")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            intent = Intent()
            intent.setAction(Intent.ACTION_SEND)
            intent.putExtra(Intent.EXTRA_TEXT, Str("Стройка и ремонт — расчёт:\n" + text))
            intent.setType("text/plain")
            PythonActivity.mActivity.startActivity(
                Intent.createChooser(intent, Str("Отправить результат")))
        except Exception:
            pass


if __name__ == "__main__":
    try:
        RepairApp().run()
    except Exception:
        import traceback
        DEBUG_TB = traceback.format_exc()
        traceback.print_exc()
        try:
            DebugApp().run()
        except Exception:
            traceback.print_exc()

