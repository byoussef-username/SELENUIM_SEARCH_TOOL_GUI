import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

from selenuim_search import SITES, make_driver, scrape_site, filter_results, write_csv


all_results = []


def log(message):
    output.insert(tk.END, message + "\n")
    output.see(tk.END)
    root.update()


def run_search():
    query = entry_query.get().strip()
    if not query:
        messagebox.showwarning("Attention", "Entrez un terme de recherche.")
        return

    min_price = entry_min.get().strip()
    max_price = entry_max.get().strip()
    min_price = float(min_price) if min_price else None
    max_price = float(max_price) if max_price else None

    selected_sites = [key for key, var in site_vars.items() if var.get()]
    if not selected_sites:
        messagebox.showwarning("Attention", "Cochez au moins un site.")
        return

    button_search.config(state=tk.DISABLED)
    output.delete("1.0", tk.END)
    all_results.clear()
    button_save.config(state=tk.DISABLED)

    thread = threading.Thread(
        target=do_search, args=(
            query, min_price, max_price, selected_sites), daemon=True
    )
    thread.start()


def do_search(query, min_price, max_price, selected_sites):
    query_words = query.split()
    log(f"Recherche: {query}\n")

    try:
        driver = make_driver()
    except Exception as e:
        log(f"Erreur: impossible de lancer Chrome ({e})")
        button_search.config(state=tk.NORMAL)
        return

    try:
        for key in selected_sites:
            site_cfg = SITES[key]
            raw_results = scrape_site(driver, site_cfg, query)
            kept = filter_results(
                raw_results, query_words, min_price, max_price)
            log(f"[{site_cfg['name']}] {len(kept)} résultat(s) retenu(s) sur {len(raw_results)} trouvé(s).")

            for r in kept:
                all_results.append({"site": site_cfg["name"], **r})
                log(f"   - {r['titre']} — {r['prix']} DH — {r['lien']}")
    finally:
        driver.quit()

    log(f"\nTerminé. {len(all_results)} résultat(s) au total.")
    button_search.config(state=tk.NORMAL)
    if all_results:
        button_save.config(state=tk.NORMAL)


def save_csv():
    if not all_results:
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("Fichier CSV", "*.csv")],
        initialfile="resultats.csv",
    )
    if path:
        write_csv(all_results, path)
        messagebox.showinfo(
            "Enregistré", f"Résultats enregistrés dans:\n{path}")


root = tk.Tk()
root.title("Comparateur de prix")
root.geometry("700x550")

frame_top = tk.Frame(root)
frame_top.pack(fill="x", padx=10, pady=10)

tk.Label(frame_top, text="Recherche:").grid(row=0, column=0, sticky="w")
entry_query = tk.Entry(frame_top, width=40)
entry_query.grid(row=0, column=1, columnspan=3, sticky="we", padx=5)

tk.Label(frame_top, text="Prix min:").grid(
    row=1, column=0, sticky="w", pady=(5, 0))
entry_min = tk.Entry(frame_top, width=10)
entry_min.grid(row=1, column=1, sticky="w", pady=(5, 0))

tk.Label(frame_top, text="Prix max:").grid(
    row=1, column=2, sticky="w", pady=(5, 0))
entry_max = tk.Entry(frame_top, width=10)
entry_max.grid(row=1, column=3, sticky="w", pady=(5, 0))

frame_sites = tk.Frame(root)
frame_sites.pack(fill="x", padx=10)

tk.Label(frame_sites, text="Sites:").pack(side="left")
site_vars = {}
for key, cfg in SITES.items():
    var = tk.BooleanVar(value=True)
    site_vars[key] = var
    tk.Checkbutton(frame_sites, text=cfg["name"], variable=var).pack(
        side="left", padx=5)

frame_buttons = tk.Frame(root)
frame_buttons.pack(fill="x", padx=10, pady=10)

button_search = tk.Button(frame_buttons, text="Rechercher", command=run_search)
button_search.pack(side="left")

button_save = tk.Button(frame_buttons, text="Enregistrer CSV",
                        command=save_csv, state=tk.DISABLED)
button_save.pack(side="left", padx=10)

output = scrolledtext.ScrolledText(root, wrap=tk.WORD)
output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

root.mainloop()
