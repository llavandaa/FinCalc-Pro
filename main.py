import tkinter as tk  # Основная библиотека для GUI
from tkinter import ttk, messagebox, simpledialog, filedialog
import requests  # Для запросов к API курса валют
import json  # Для работы с историей в формате JSON
import os  # Для проверки существования файла
from datetime import datetime  # Для работы с датами
from tkinter import font as tkfont  # Для шрифтов (не используется, но можно расширить)
import sv_ttk  # Тема оформления приложения
from dateutil import parser  # Для разбора строковых дат
from bs4 import BeautifulSoup

# -----------------------------
# Конфигурация приложения
# -----------------------------
BG_COLOR = "#1E1E1E"      # Цвет фона (пока не применяется)
ACCENT_COLOR = "#2E8B57"  # Акцентный цвет для кнопок
TEXT_COLOR = "#FFFFFF"    # Цвет текста
FONT_NAME = "Segoe UI"    # Шрифт по умолчанию
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) # Папка скрипта
HISTORY_FILE = os.path.join(SCRIPT_DIR, "history.json") # Файл истории в каталоге скрипта
VERSION = "1.4.6-2r"


class ModernApp(tk.Tk):
    """
    Основное окно приложения: взаимодействие с пользователем,
    ввод данных, вывод истории и статистики.
    """
    def __init__(self):
        super().__init__()
        self.title("FinCalc Pro")
        self.geometry("1200x700")

        # Загрузка истории
        self.history = self.load_history()
        sv_ttk.use_light_theme()
        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.configure("Accent.TButton",
                             foreground=TEXT_COLOR,
                             background=ACCENT_COLOR,
                             font=(FONT_NAME, 10, 'bold'))
        self.style.map("Accent.TButton",
                       background=[('active', '#3CB371')])

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(expand=True, fill="both")

        # Новая операция
        input_frame = ttk.LabelFrame(main_frame, text=" Новая операция ", padding=15)
        input_frame.pack(fill="x", pady=10)
        ttk.Label(input_frame, text="Номер заказа:").grid(row=0, column=0,
                                                           padx=5, pady=5, sticky="w")
        self.order_id_entry = ttk.Entry(input_frame, width=30)
        self.order_id_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(input_frame, text="Способ оплаты:").grid(row=1, column=0,
                                                              padx=5, pady=5, sticky="w")
        self.payment_method = tk.StringVar(value="card")
        methods_frame = ttk.Frame(input_frame)
        methods_frame.grid(row=1, column=1, sticky="ew")
        for i, (text, val) in enumerate([("💳 Карта", "card"),
                                         ("🏢 ИП", "ip"),
                                         ("🇪🇺 Euro", "euro")]):
            rb = ttk.Radiobutton(methods_frame, text=text,
                                 value=val, variable=self.payment_method)
            rb.pack(side="left", padx=10, ipadx=5, ipady=3)
            methods_frame.columnconfigure(i, weight=1)

        ttk.Button(input_frame, text="Рассчитать",
                  command=self.process_order,
                  style="Accent.TButton").grid(row=2, column=1,
                                                pady=15, sticky="e")

        # История операций
        history_frame = ttk.LabelFrame(main_frame,
                                      text=" История операций ", padding=15)
        history_frame.pack(expand=True, fill="both", pady=10)

        cols = (
            "id", "method", "date", "rub", "eur", "eur_rate",
            "fee", "commission", "dirty", "mgr_fee", "clean"
        )
        self.history_tree = ttk.Treeview(history_frame,
                                        columns=cols, show="headings")
        headers = {
            "id": "№", "method": "Способ оплаты", "date": "Дата",
            "rub": "Сумма (RUB)", "eur": "Сумма (EUR)",
            "eur_rate": "Курс EUR", "fee": "Гонорар",
            "commission": "Комиссия", "dirty": "Грязный остаток",
            "mgr_fee": "Зарплата\nменеджера", "clean": "Чистый остаток"
        }
        for c in cols:
            self.history_tree.heading(c, text=headers[c])
            self.history_tree.column(c, width=100, anchor="center")

        self.history_tree.pack(expand=True, fill="both")
        self.history_tree.bind("<Double-1>", self.show_history_item)
        self.history_tree.bind("<Button-3>", self.show_context_menu)
        self.history_tree.bind("<Delete>", lambda e: self.delete_selected_items())
        self.deleted_entries = []
        self.context_menu = None
        self.update_history_list()

        # Статистика
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill="x", pady=10)
        ttk.Button(stats_frame, text="Статистика за период",
                  command=self.show_stats_dialog).pack(side="left")

    def show_context_menu(self, event):
        # Если уже было меню — уберём его
        if self.context_menu:
            try:
                self.context_menu.unpost()
            except:
                pass

        # Определяем строку и выделяем
        item = self.history_tree.identify_row(event.y)
        if not item:
            return
        self.history_tree.selection_set(item)

        # Создаём (или переиспользуем) меню
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(
            label="Удалить", command=self.delete_selected_items
        )
        if self.deleted_entries:
            self.context_menu.add_command(
                label="Отменить удаление", command=self.undo_delete
            )

        # Показываем меню ровно в одной копии
        self.context_menu.post(event.x_root, event.y_root)
    

    def delete_selected_items(self):
        items = self.history_tree.selection()
        if not items:
            return
        if not messagebox.askyesno("Удаление",
                                   f"Удалить {len(items)} запись(и)?"):
            return
        to_delete = set()
        deleted = []
        for iid in items:
            vals = self.history_tree.item(iid, "values")
            if vals and vals[0] != "Total":
                to_delete.add(str(vals[0]))
        remaining = []
        for entry in self.history:
            if str(entry["id"]) in to_delete:
                deleted.append(entry)
            else:
                remaining.append(entry)
        if deleted:
            self.deleted_entries = deleted
            self.history = remaining
            self.save_history()
            self.update_history_list()

    def undo_delete(self):
        if not self.deleted_entries:
            return
        self.history.extend(self.deleted_entries)
        self.history.sort(key=lambda x: x["id"])
        self.deleted_entries = []
        self.save_history()
        self.update_history_list()

    def process_order(self):
        oid = self.order_id_entry.get().strip()
        if not oid:
            self.show_error("Ошибка", "Введите номер заказа")
            return
        try:
            m = self.payment_method.get()
            if m == "card":
                report = self.process_card()
            elif m == "euro":
                report = self.process_euro()
            elif m == "ip":
                report = self.process_ip()
            else:
                raise ValueError("Неизвестный метод оплаты")
            self.save_to_history(oid, m, report)
            self.update_history_list()
            self.show_report(report)
            self.order_id_entry.delete(0, tk.END)
        except Exception as e:
            self.show_error("Ошибка", str(e))

    def process_card(self):
        amount = self.ask_float("Карта РФ", "Сумма поступления:")
        ret = simpledialog.askfloat("Возврат клиенту",
                                    "Введите сумму возврата (0, если нет):",
                                    parent=self) or 0.0
        fee = self.ask_float("Карта РФ", "Гонорар переводчика:")
        commission = self.ask_float("Карта РФ", "Комиссия банка:")
        tax = simpledialog.askfloat("Налог",
                                    "Введите сумму налога (0, если нет):",
                                    parent=self) or 0.0
        gryaz = amount - fee - commission - ret - tax
        report = self.generate_report("Карта РФ", gryaz)
        report.update({
            "Сумма RUB": amount,
            "Сумма EUR": 0.0,
            "Курс EUR": 0.0,
            "Гонорар переводчика": fee,
            "Комиссия банка": commission,
            "Возврат": ret,
            "Налог": tax,
            "Инвойс": 0.0
        })
        return report

    def process_euro(self):
        eur_rate = self.get_eur_rate()
        amount_eur = self.ask_float("Euro счет", "Сумма в EUR:")
        ret_e = simpledialog.askfloat("Возврат (EUR)",
                                       "Сумма возврата (0, если нет):",
                                       parent=self) or 0.0
        fee_e = self.ask_float("Euro счет",
                               "Гонорар переводчика (EUR):")
        tax_e = simpledialog.askfloat("Налог (EUR)",
                                       "Сумма налога (0, если нет):",
                                       parent=self) or 0.0
        inv_e = simpledialog.askfloat("Инвойс (EUR)",
                                       "Сумма работы с инвойсом (0, если нет):",
                                       parent=self) or 0.0
        rub = amount_eur * eur_rate
        ret_r = ret_e * eur_rate
        fee_r = fee_e * eur_rate
        tax_r = tax_e * eur_rate
        inv_r = inv_e * eur_rate
        commission = rub * 0.03 + 10 * eur_rate
        gryaz = rub - ret_r - fee_r - commission - tax_r - inv_r
        report = self.generate_report("Euro счет", gryaz)
        report.update({
            "Сумма RUB": rub,
            "Курс EUR": eur_rate,
            "Сумма EUR": amount_eur,
            "Гонорар переводчика": fee_r,
            "Комиссия банка": commission,
            "Возврат": ret_r,
            "Налог": tax_r,
            "Инвойс": inv_r
        })
        return report

    def process_ip(self):
        amount = self.ask_float("ИП РФ", "Общая сумма:")
        ret = simpledialog.askfloat("Возврат клиенту",
                                    "Введите сумму возврата (0, если нет):",
                                    parent=self) or 0.0
        fee = self.ask_float("ИП РФ", "Гонорар переводчика:")
        commission = self.ask_float("ИП РФ", "Комиссия банка:")
        tax = amount * 0.07
        inv = 0.0
        gryaz = amount - tax - fee - commission - ret
        report = self.generate_report("ИП РФ", gryaz)
        report.update({
            "Сумма RUB": amount,
            "Сумма EUR": 0.0,
            "Курс EUR": 0.0,
            "Гонорар переводчика": fee,
            "Комиссия банка": commission,
            "Возврат": ret,
            "Налог": tax,
            "Инвойс": inv
        })
        return report

    def ask_date_format(self, title, promt):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.grab_set()
        ttk.Label(dlg, text=promt).pack(padx=10, pady=(10, 0))
        date_entry = ttk.Entry(dlg)
        date_entry.pack(padx=10, pady=5)
        date_entry.focus_set
        def fmt(e):
            w = e.widget
            t = w.get().replace(".", "").replace("/", "")[:8]
            if len(t) >= 2:
                t = f"{t[:2]}.{t[2:4]}.{t[4:8]}"
            w.delete(0, tk.END)
            w.insert(0, t.strip('.'))
        date_entry.bind("<KeyRelease>", fmt)
        result = {"date": None}
        def on_ok(): result["date"] = date_entry.get().strip(); dlg.destroy()
        def on_cancel(): dlg.destroy()
        btn = ttk.Frame(dlg); btn.pack(pady=10)
        ttk.Button(btn, text="OK", command=on_ok).pack(side="left", padx=5)
        ttk.Button(btn, text="Отмена", command=on_cancel).pack(side="right", padx=5)
        self.wait_window(dlg)
        return result["date"]

    def generate_report(self, method, gryaz):
        """
        Формирует словарь итоговых данных операции:
        - Запрашивает дату заказа
        - Считает зарплату менеджера (20%)
        - Возвращает полный отчёт
        """
        manager_fee = gryaz * 0.2
        
        # Ввод даты
        date_str = self.ask_date_format(
            "Дата заказа",
            "Введите дату в формате ДД.MM.ГГГГ"
        )
        if not date_str:
            raise ValueError("Операция отменена пользователем")

        # Парсинг даты
        try:
            parsed = datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            raise ValueError("Неверный формат даты. Используйте ДД.MM.YYYY")

        # Собираем итоговый отчёт
        report = {
            "Способ": method,
            "Грязный остаток": f"{gryaz:.2f} руб.",
            "Зарплата менеджера": f"{manager_fee:.2f} руб.",
            "Чистый остаток": f"{(gryaz - manager_fee):.2f} руб.",
            "Дата": parsed.strftime("%d.%m.%Y")
        }
        return report

    def get_eur_rate(self):
        """
        Получение курса EUR→RUB с сайта x-rates.com.
        При ошибке — ручной ввод.
        """
        try:
            url = "https://www.x-rates.com/calculator/?from=EUR&to=RUB&amount=1"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/114.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(url, headers=headers, timeout=5)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            span = soup.find("span", class_="ccOutputTrail").previous_sibling
            if not span:
                raise ValueError("Не найден курс на странице X-Rates")

            return float(span.text.strip())

        except Exception as e:
            # fallback на ручной ввод
            return self.ask_float(
                "Курс EUR",
                "Не удалось получить курс автоматически.\nВведите курс вручную:"
            )

    # ------------------------------------
    # История: загрузка/сохранение/обновление
    # ------------------------------------
    def save_to_history(self, order_id, method, report):
        self.history.append({
            "id": order_id,
            "method": method,
            "date": report["Дата"],
            "report": report
        })
        self.save_history()

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def update_history_list(self):
        self.history_tree.delete(*self.history_tree.get_children())
        totals = {k: 0.0 for k in ("rub","eur","fee","commission","dirty","mgr_fee","clean")}
        for entry in self.history:
            rep = entry["report"]
            # Извлечение чисел
            rub   = float(rep.get("Сумма RUB",      rep["Грязный остаток"].split()[0]))
            eur   = float(rep.get("Сумма EUR",      0.0))
            rate  = float(rep.get("Курс EUR",        0.0))
            fee   = float(rep.get("Гонорар переводчика",0.0))
            com   = float(rep.get("Комиссия банка",  0.0))
            dirty = float(rep["Грязный остаток"].split()[0])
            mgr   = float(rep["Зарплата менеджера"].split()[0])
            clean = float(rep["Чистый остаток"].split()[0])

            totals["rub"]      += rub
            totals["eur"]      += eur
            totals["fee"]      += fee
            totals["commission"]+= com
            totals["dirty"]    += dirty
            totals["mgr_fee"]  += mgr
            totals["clean"]    += clean

            self.history_tree.insert("", "end", values=(
                entry["id"], entry["method"], rep["Дата"],
                f"{rub:.2f}", f"{eur:.2f}", f"{rate:.2f}",
                f"{fee:.2f}", f"{com:.2f}",
                f"{dirty:.2f}", f"{mgr:.2f}", f"{clean:.2f}"
            ))

        # Строка Total
        self.history_tree.insert("", "end", values=(
            "Total","", "",
            f"{totals['rub']:.2f}", f"{totals['eur']:.2f}", "",
            f"{totals['fee']:.2f}", f"{totals['commission']:.2f}",
            f"{totals['dirty']:.2f}", f"{totals['mgr_fee']:.2f}",
            f"{totals['clean']:.2f}"
        ))

    def show_history_item(self, event):
        item = self.history_tree.selection()[0]
        values = self.history_tree.item(item, "values")
        entry = next(e for e in self.history if e["id"] == values[0])
        self.show_report(entry["report"])

    def show_stats_dialog(self):
        # Создаём окно для ввода дат
        dialog = tk.Toplevel(self)
        dialog.title("Статистика за период")

        # Поля для ввода даты
        ttk.Label(dialog, text="Дата начала (ДД.ММ.ГГГГ):").grid(row=0, column=0, padx=5, pady=5)
        start_entry = ttk.Entry(dialog)
        start_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="Дата окончания (ДД.ММ.ГГГГ):").grid(row=1, column=0, padx=5, pady=5)
        end_entry = ttk.Entry(dialog)
        end_entry.grid(row=1, column=1, padx=5, pady=5)

        def format_date(event):
            widget = event.widget
            # Очищаем ввод от лишних символов, оставляем до 8 цифр
            text = widget.get().replace(".", "").replace("/", "")[:8]
            # Вставляем точки после ДД и ММ
            if len(text) >= 2:
                text = f"{text[:2]}.{text[2:4]}.{text[4:8]}"
            widget.delete(0, tk.END)
            widget.insert(0, text.strip('.'))

        # Привязываем форматирование к полям ввода дат
        start_entry.bind("<KeyRelease>", format_date)
        end_entry.bind("<KeyRelease>", format_date)

        def calculate():
            try:
                # Получаем и парсим даты
                start = datetime.strptime(start_entry.get(), "%d.%m.%Y")
                end = datetime.strptime(end_entry.get(), "%d.%m.%Y")

                total_fee = 0.0
                total_clean = 0.0

                for entry in self.history:
                    # Парсим дату из истории
                    entry_date = datetime.strptime(entry["report"]["Дата"], "%d.%m.%Y")

                    # Проверяем попадание в диапазон
                    if start <= entry_date <= end:
                        total_fee += float(entry["report"]["Зарплата менеджера"].split()[0])
                        total_clean += float(entry["report"]["Чистый остаток"].split()[0])

                # Отображаем результаты
                messagebox.showinfo("Результаты", 
                                    f"Общая зарплата менеджеров: {total_fee:.2f} руб.\n"
                                    f"Общий чистый остаток: {total_clean:.2f} руб.")

            except ValueError as ve:
                self.show_error("Ошибка формата", f"Некорректная дата: {str(ve)}")
            except Exception as e:
                self.show_error("Ошибка", f"Ошибка расчета: {str(e)}")

        # Кнопка расчета статистики
        ttk.Button(dialog, text="Рассчитать", command=calculate).grid(row=2, columnspan=2, pady=10)


    # Вспомогательные методы:
    def ask_float(self, title, prompt):
        val = simpledialog.askfloat(title, prompt, parent=self)
        if val is None:
            raise ValueError("Операция отменена")
        return val

    def show_report(self, report):
        dlg = tk.Toplevel(self)
        dlg.title("Детали операции")
        for i, (k, v) in enumerate(report.items()):
            ttk.Label(dlg, text=f"{k}:").grid(row=i, column=0, padx=5, pady=2, sticky="e")
            ttk.Label(dlg, text=v).grid(row=i, column=1, padx=5, pady=2, sticky="w")

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False)

    def show_error(self, title, msg):
        messagebox.showerror(title, msg)


if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()
