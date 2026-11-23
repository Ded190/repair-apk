import os
import sys
import time
import traceback

STEPS = []


def _toast(msg):
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Toast = autoclass("android.widget.Toast")
        Toast.makeText(PythonActivity.mActivity, msg, Toast.LENGTH_LONG).show()
        return True
    except Exception:
        return False


def _log(msg):
    STEPS.append(msg)
    try:
        with open("/sdcard/Download/repaircalc_probe.txt", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    try:
        d = os.environ.get("ANDROID_PRIVATE") or "/data/data/org.ded190.repaircalc/files"
        with open(os.path.join(d, "probe_log.txt"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


try:
    _log("ШАГ 0: " + time.strftime("%d.%m %H:%M:%S") + " - Python запущен")
    _toast("ПРОБА: Python жив")
    _log("ШАГ 1: импортирую kivy")
    from kivy.app import App
    from kivy.uix.label import Label
    _log("ШАГ 2: kivy импортирован")
    _toast("ПРОБА: kivy работает")

    class ProbeApp(App):
        title = "Проба"

        def build(self):
            _log("ШАГ 3: build() начался")
            lbl = Label(text="ПРОБА УСПЕШНА.\n\nPython и Kivy живы.\n\nНапиши Алисе: ПРОБА ОК",
                        font_size="22sp", halign="center", valign="middle")
            lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            _log("ШАГ 4: экран готов")
            return lbl

    _log("ШАГ 5: запускаю главный цикл")
    _toast("ПРОБА: запускаю")
    ProbeApp().run()
    _log("ШАГ 6: RUN OK - всё работает")
except Exception:
    tb = traceback.format_exc()
    _log("КРАШ:\n" + tb)
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        it = Intent()
        it.setAction(Intent.ACTION_SEND)
        it.setType("text/plain")
        it.putExtra(Intent.EXTRA_TEXT,
                    "Проба упала:\n" + "\n".join(STEPS) + "\n\n" + tb)
        PythonActivity.mActivity.startActivity(
            Intent.createChooser(it, "Отправить Алисе"))
    except Exception:
        pass
