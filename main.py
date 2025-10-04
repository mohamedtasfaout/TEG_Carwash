import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, Toplevel, simpledialog, ttk
from barcode import Code128
from barcode.writer import ImageWriter
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw, ImageFont
from io import BytesIO
import platform
import subprocess

# ---------- Mot de passe ----------
PASSWORD = "sarlteg2019"

def check_password():
    pwd = simpledialog.askstring("Mot de passe", "Entrer le mot de passe :", show="*")
    if pwd == PASSWORD:
        return True
    elif pwd is None:
        return False
    else:
        messagebox.showerror("Erreur", "Mot de passe incorrect")
        return False

# ---------- Imprimer multi-plateforme ----------
def print_file(filepath):
    try:
        if platform.system() == "Windows":
            os.startfile(filepath, "print")
        else:
            try:
                subprocess.run(["lp", filepath], check=True)
            except Exception:
                subprocess.run(["lpr", filepath], check=True)
    except Exception as e:
        messagebox.showerror("Erreur impression", str(e))

# ---------- Base de données ----------
conn = sqlite3.connect("teg.db")
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                car_type TEXT,
                brand TEXT,
                plate TEXT,
                created_at TEXT
            )""")
conn.commit()

# ---------- Génération code-barres ----------
def generate_barcode(code):
    barcode_img_io = BytesIO()
    barcode = Code128(code, writer=ImageWriter())
    barcode.write(barcode_img_io, options={
        "write_text": False,
        "module_width": 0.6,
        "module_height": 60,
        "quiet_zone": 8
    })
    barcode_img_io.seek(0)

    img = Image.open(barcode_img_io).convert("RGB")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), code, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w, h = img.size
    new_img = Image.new("RGB", (w, h + text_h + 20), "white")
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    draw.text(((w - text_w) / 2, h + 5), code, font=font, fill="black")
    return new_img

# ---------- Génération ticket ----------
def generate_ticket(master=False):
    if master and not check_password():
        return

    car_type = entry_car_type.get().strip()
    brand = entry_brand.get().strip()
    plate = entry_plate.get().strip()

    if not master and (not car_type or not brand or not plate):
        messagebox.showerror("Erreur", "Veuillez remplir tous les champs")
        return

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if master:
        c.execute("SELECT id FROM tickets WHERE code='MASTER'")
        if c.fetchone():
            messagebox.showinfo("Info", "Un ticket MASTER existe déjà.")
            return
        code = "MASTER"
        c.execute("INSERT INTO tickets (code, car_type, brand, plate, created_at) VALUES (?, ?, ?, ?, ?)",
                  (code, car_type, brand, plate, created_at))
        conn.commit()
    else:
        c.execute("INSERT INTO tickets (code, car_type, brand, plate, created_at) VALUES (?, ?, ?, ?, ?)",
                  ("PENDING", car_type, brand, plate, created_at))
        conn.commit()
        ticket_id = c.lastrowid
        code = f"TEG-{ticket_id:05d}"
        c.execute("UPDATE tickets SET code=? WHERE id=?", (code, ticket_id))
        conn.commit()

    c.execute("SELECT COUNT(*) FROM tickets WHERE plate LIKE ?", (f"%{plate}%",))
    passage_count = c.fetchone()[0]

    barcode_img = generate_barcode(code).resize((350, 150))
    tk_img = ImageTk.PhotoImage(barcode_img)

    preview = Toplevel(root)
    preview.title("Prévisualisation Ticket")
    preview.geometry("420x550")
    preview.configure(bg="#f5f5f5")

    tk.Label(preview, text=f"Type : {car_type}", font=("Arial", 12), bg="#f5f5f5").pack(pady=5)
    tk.Label(preview, text=f"Marque : {brand}", font=("Arial", 12), bg="#f5f5f5").pack(pady=5)
    tk.Label(preview, text=f"Matricule : {plate}", font=("Arial", 12), bg="#f5f5f5").pack(pady=5)
    tk.Label(preview, text=f"Date : {created_at}", font=("Arial", 10), bg="#f5f5f5").pack(pady=5)
    tk.Label(preview, text=f"Nombre de passages : {passage_count}", font=("Arial", 12, "bold"), bg="#f5f5f5").pack(pady=5)

    lbl_img = tk.Label(preview, image=tk_img, bg="#f5f5f5")
    lbl_img.image = tk_img
    lbl_img.pack(pady=10)

    def print_ticket():
        try:
            ticket_file = "ticket_temp.png"
            W, H = 450, 500
            ticket_img_draw = Image.new("RGB", (W, H), "white")
            d = ImageDraw.Draw(ticket_img_draw)
            try:
                font_title = ImageFont.truetype("arial.ttf", 22)
                font_text = ImageFont.truetype("arial.ttf", 18)
            except:
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()

            def center_text(text, y, font, fill="black"):
                bbox = d.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                x = (W - text_w) // 2
                d.text((x, y), text, font=font, fill=fill)

            center_text("TEG CAR WASH", 10, font_title)
            center_text("Ouvert 7/7", 40, font_text)
            center_text("Tel : 0561979262", 70, font_text)
            center_text(f"Type: {car_type}", 120, font_text)
            center_text(f"Marque: {brand}", 150, font_text)
            center_text(f"Matricule: {plate}", 180, font_text)
            center_text(f"Date: {created_at}", 210, font_text)
            center_text(f"Passages: {passage_count}", 235, font_text)
            bx = (W - barcode_img.width) // 2
            ticket_img_draw.paste(barcode_img, (bx, 260))
            center_text("Merci pour votre visite", 430, font_text)

            ticket_img_draw.save(ticket_file)
            print_file(ticket_file)
            messagebox.showinfo("Impression", "Ticket envoyé à l'imprimante")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    tk.Button(preview, text="Imprimer", command=print_ticket,
              bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
              relief="flat", padx=10, pady=5).pack(pady=10)

# ---------- Impression Rapports Pro ----------
def print_report(rows, title="Rapport"):
    try:
        W, H = 900, 1200
        rapport_img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(rapport_img)

        try:
            font_title = ImageFont.truetype("arial.ttf", 32)
            font_sub = ImageFont.truetype("arial.ttf", 22)
            font_text = ImageFont.truetype("arial.ttf", 18)
        except:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_text = ImageFont.load_default()

        d.text((W//2 - 120, 20), "TEG CAR WASH", font=font_title, fill="black")
        d.text((W//2 - 80, 70), "Ouvert 7/7", font=font_sub, fill="black")
        d.text((W//2 - 120, 100), "Tél: 0561979262", font=font_sub, fill="black")
        d.text((W//2 - 200, 140), title, font=font_sub, fill="black")
        d.line((50, 170, W-50, 170), fill="black", width=3)

        headers = ["ID", "Code", "Type", "Marque", "Plaque", "Date"]
        col_widths = [60, 140, 120, 140, 140, 250]
        x_positions = [50]
        for w_col in col_widths[:-1]:
            x_positions.append(x_positions[-1] + w_col)

        y = 200
        for i, head in enumerate(headers):
            d.text((x_positions[i], y), head, font=font_sub, fill="black")
        y += 35
        d.line((50, y, W-50, y), fill="black", width=2)
        y += 10

        row_height = 30
        for idx, row in enumerate(rows):
            if y + row_height > H - 200:
                break
            if idx % 2 == 0:
                d.rectangle([50, y-5, W-50, y+row_height], fill="#f0f0f0")
            values = [str(r or "") for r in row]
            for i, val in enumerate(values):
                d.text((x_positions[i], y), val, font=font_text, fill="black")
            y += row_height + 5

        count = len(rows)
        y += 40
        d.text((50, y), f"Nombre total de passages : {count}", font=font_sub, fill="black")
        y += 40
        d.line((50, y, W-50, y), fill="black", width=2)
        y += 20
        d.text((50, y), "Merci pour votre confiance", font=font_sub, fill="black")
        d.text((W-300, y), "Signature du caissier: ..................", font=font_sub, fill="black")

        rapport_file = "rapport.png"
        rapport_img.save(rapport_file)
        print_file(rapport_file)
        messagebox.showinfo("Impression", "Rapport envoyé à l'imprimante")
    except Exception as e:
        messagebox.showerror("Erreur", str(e))

# ---------- Affichage Rapport propre ----------
def view_report(rows, title="Rapport"):
    if not rows:
        messagebox.showinfo("Rapport", "Aucun ticket trouvé")
        return

    win = tk.Toplevel(root)
    win.title(title)
    win.geometry("1000x600")
    win.configure(bg="#f0f0f0")

    tk.Label(win, text=f"*** {title} ***", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(pady=10)

    frame_table = tk.Frame(win)
    frame_table.pack(fill="both", expand=True, padx=10, pady=10)

    columns = ("ID", "Code", "Type", "Marque", "Plaque", "Date")
    tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=20)

    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor="center")

    for idx, row in enumerate(rows):
        tag = "even" if idx % 2 == 0 else "odd"
        tree.insert("", "end", values=row, tags=(tag,))
    tree.tag_configure("even", background="#ffffff")
    tree.tag_configure("odd", background="#e8e8e8")

    tree.pack(side="left", fill="both", expand=True)

    scrollbar_v = ttk.Scrollbar(frame_table, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_v.set)
    scrollbar_v.pack(side="right", fill="y")

    scrollbar_h = ttk.Scrollbar(win, orient="horizontal", command=tree.xview)
    tree.configure(xscrollcommand=scrollbar_h.set)
    scrollbar_h.pack(fill="x")

    count = len(rows)
    tk.Label(win, text=f"Nombre total de passages : {count}", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=5)

    tk.Button(win, text="Imprimer", command=lambda: print_report(rows, title),
              bg="#1976d2", fg="white", font=("Arial", 11, "bold"), relief="flat").pack(pady=8)

# ---------- Rapports utilitaires ----------
def view_daily_report():
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT * FROM tickets WHERE created_at LIKE ?", (today + "%",))
    rows = c.fetchall()
    view_report(rows, title=f"Rapport Journalier - {today}")

def view_all_report():
    if not check_password():
        return
    c.execute("SELECT * FROM tickets ORDER BY id ASC")
    rows = c.fetchall()
    view_report(rows, title="Rapport Complet")

def search_by_plate():
    if not check_password():
        return
    plate = simpledialog.askstring("Recherche", "Entrer la matricule :")
    if not plate:
        return
    c.execute("SELECT * FROM tickets WHERE plate LIKE ?", (f"%{plate}%",))
    rows = c.fetchall()
    view_report(rows, title=f"Recherche par Matricule - {plate}")

def search_by_date():
    if not check_password():
        return
    date = simpledialog.askstring("Recherche", "Entrer la date (YYYY-MM-DD) :")
    if not date:
        return
    c.execute("SELECT * FROM tickets WHERE created_at LIKE ?", (date + "%",))
    rows = c.fetchall()
    view_report(rows, title=f"Recherche par Date - {date}")

def view_report_between_dates():
    if not check_password():
        return
    start = simpledialog.askstring("Rapport", "Entrer la date de début (YYYY-MM-DD) :")
    end = simpledialog.askstring("Rapport", "Entrer la date de fin (YYYY-MM-DD) :")
    if not start or not end:
        return
    c.execute("SELECT * FROM tickets WHERE created_at BETWEEN ? AND ? ORDER BY created_at ASC",
              (start + " 00:00:00", end + " 23:59:59"))
    rows = c.fetchall()
    view_report(rows, title=f"Rapport entre {start} et {end}")

def view_monthly_report():
    if not check_password():
        return
    month = simpledialog.askstring("Rapport", "Entrer le mois (MM) :")
    year = simpledialog.askstring("Rapport", "Entrer l'année (YYYY) :")
    if not month or not year:
        return
    c.execute("SELECT * FROM tickets WHERE strftime('%m', created_at)=? AND strftime('%Y', created_at)=?",
              (month.zfill(2), year))
    rows = c.fetchall()
    view_report(rows, title=f"Rapport Mensuel - {month}/{year}")

# ---------- Interface stylée ----------
root = tk.Tk()
root.title("TEG Carwash - Ticket Generator")
root.geometry("420x650")
root.configure(bg="#e8f0fe")

tk.Label(root, text="TEG CARWASH", font=("Arial", 18, "bold"),
         fg="#0d47a1", bg="#e8f0fe").pack(pady=12)
tk.Label(root, text="Gestion des Tickets", font=("Arial", 12),
         fg="#333", bg="#e8f0fe").pack(pady=5)

frame_inputs = tk.Frame(root, bg="#e8f0fe")
frame_inputs.pack(pady=12)

tk.Label(frame_inputs, text="Type de voiture :", bg="#e8f0fe").grid(row=0, column=0, sticky="w", pady=6)
entry_car_type = tk.Entry(frame_inputs, width=28, relief="solid")
entry_car_type.grid(row=0, column=1, pady=6)

tk.Label(frame_inputs, text="Marque :", bg="#e8f0fe").grid(row=1, column=0, sticky="w", pady=6)
entry_brand = tk.Entry(frame_inputs, width=28, relief="solid")
entry_brand.grid(row=1, column=1, pady=6)

tk.Label(frame_inputs, text="Matricule :", bg="#e8f0fe").grid(row=2, column=0, sticky="w", pady=6)
entry_plate = tk.Entry(frame_inputs, width=28, relief="solid")
entry_plate.grid(row=2, column=1, pady=6)

frame_buttons = tk.Frame(root, bg="#e8f0fe")
frame_buttons.pack(pady=18)

def styled_button(text, command, color="#1976d2"):
    return tk.Button(frame_buttons, text=text, command=command,
                     bg=color, fg="white", width=30, height=1,
                     font=("Arial", 11, "bold"), relief="flat", pady=6)

styled_button("Générer Ticket", lambda: generate_ticket(master=False), "#1976d2").pack(pady=6)
styled_button("Générer MASTER", lambda: generate_ticket(master=True), "#c62828").pack(pady=6)
styled_button("Voir Rapport Journalier", view_daily_report, "#388e3c").pack(pady=6)
styled_button("Voir Rapport Complet", view_all_report, "#6a1b9a").pack(pady=6)
styled_button("Recherche par Matricule", search_by_plate, "#00838f").pack(pady=6)
styled_button("Recherche par Date", search_by_date, "#5d4037").pack(pady=6)
styled_button("Rapport entre 2 dates", view_report_between_dates, "#ef6c00").pack(pady=6)
styled_button("Rapport Mensuel", view_monthly_report, "#9e9d24").pack(pady=6)

root.mainloop()
