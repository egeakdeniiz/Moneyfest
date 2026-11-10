import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from models import DeadlockEngine

class DeadlockSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Deadlock Simulator & Banker's Algorithm (Pro Edition)")
        self.root.geometry("1400x920")

        self.engine = DeadlockEngine()

        self.alloc_entries = []
        self.max_entries = []
        self.prio_entries = []
        self.cost_entries = []

        self.is_dark_mode = False
        self.terminated_processes = set()  # sadece öldürülen kurban süreçler (kırmızıılar)
        self.completed_processes = set()   # işini bitiren süreçler (yeşil kısımlar)
        
        self.is_animating = False
        self.anim_speed_ms = 900
        self.start_timer = 0
        self.elapsed_time = 0.0
        self.timer_running = False

        self.setup_ui()

    def setup_ui(self):
        self.style = ttk.Style()
        self.apply_theme()

        self.left_frame = ttk.Frame(self.root, padding="10")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        top_bar = ttk.Frame(self.left_frame)
        top_bar.pack(fill=tk.X, pady=5)
        
        ttk.Label(top_bar, text="Deadlock Control Center", font=("Helvetica", 11, "bold")).pack(side=tk.LEFT)
        
        self.health_label = tk.Label(top_bar, text="HEALTHY", bg="#2ecc71", fg="white", font=("Helvetica", 8, "bold"), padx=6, pady=2)
        self.health_label.pack(side=tk.LEFT, padx=6)

        self.theme_btn = ttk.Button(top_bar, text=" Dark Mode", command=self.toggle_theme)
        self.theme_btn.pack(side=tk.RIGHT)

        # HAZIR SENARYOLAR
        preset_group = ttk.LabelFrame(self.left_frame, text=" Hazır Senaryolar (Presets) ", padding="5")
        preset_group.pack(fill=tk.X, pady=4)
        
        self.preset_cb = ttk.Combobox(preset_group, values=[
            "Deadlock (Kilitlenme Senaryosu)",
            "Safe State (Güvenli Senaryo)",
            "High Starvation (Kaynak Açlığı)"
        ], state="readonly")
        self.preset_cb.current(0)
        self.preset_cb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(preset_group, text="Yükle", command=self.load_preset).pack(side=tk.RIGHT, padx=2)

        # BOYUT AYARLARI
        dim_group = ttk.LabelFrame(self.left_frame, text=" Boyut Ayarları ", padding="5")
        dim_group.pack(fill=tk.X, pady=4)
        dim_row = ttk.Frame(dim_group)
        dim_row.pack(fill=tk.X, pady=2)
        ttk.Label(dim_row, text="Süreç (P):").pack(side=tk.LEFT, padx=2)
        self.p_spin = ttk.Spinbox(dim_row, from_=1, to=6, width=3)
        self.p_spin.set(str(self.engine.num_processes))
        self.p_spin.pack(side=tk.LEFT, padx=2)
        ttk.Label(dim_row, text="Kaynak (R):").pack(side=tk.LEFT, padx=2)
        self.r_spin = ttk.Spinbox(dim_row, from_=1, to=5, width=3)
        self.r_spin.set(str(self.engine.num_resources))
        self.r_spin.pack(side=tk.LEFT, padx=2)
        ttk.Button(dim_row, text="Uygula", command=self.apply_dimensions).pack(side=tk.LEFT, padx=5)

        # MATRİS GİRİŞİ
        self.input_group = ttk.LabelFrame(self.left_frame, text=" Matris Veri Girişi ", padding="5")
        self.input_group.pack(fill=tk.X, pady=5)
        self.create_matrix_inputs()

        # ADIM ADIM TÜM KİLİTLERİ ÇÖZEN MOTOR
        step_group = ttk.LabelFrame(self.left_frame, text=" Tüm Kilitleri Adım Adım Çöz ", padding="5")
        step_group.pack(fill=tk.X, pady=5)

        ttk.Button(step_group, text=" Adım Adım Tüm Kilitleri Çöz", command=self.start_sequential_solution_animation).pack(fill=tk.X, pady=4)

        timer_frame = ttk.Frame(step_group)
        timer_frame.pack(fill=tk.X, pady=4)
        ttk.Label(timer_frame, text=" Geçen Süre:", font=("Helvetica", 8, "bold")).pack(side=tk.LEFT)
        self.timer_label = tk.Label(timer_frame, text="0.000 s (0 ms)", font=("Consolas", 10, "bold"), fg="#e74c3c")
        self.timer_label.pack(side=tk.RIGHT)

        # SPESİFİK STRATEJİYLE TEK KURBAN ÖLDÜRÜCÜ
        strategy_group = ttk.LabelFrame(self.left_frame, text=" Akıllı Kilitlenme Çözümü ", padding="5")
        strategy_group.pack(fill=tk.X, pady=5)

        self.strategy_cb = ttk.Combobox(strategy_group, values=[
            "Lowest Priority (En Düşük Öncelikliyi Öldür)",
            "Lowest Termination Cost (En Az Maliyetliyi Kurban Et)",
            "Victim: Max Allocation (En Çok Kaynak Tüketen)",
            "Resource Preemption (Kaynak Geri Alma)"
        ], state="readonly")
        self.strategy_cb.current(0)
        self.strategy_cb.pack(fill=tk.X, pady=4)

        ttk.Button(strategy_group, text=" Seçilen Stratejiyle Çöz", command=self.resolve_single_victim_manual).pack(fill=tk.X, pady=2)

        # RAPOR VE LOG KAYDETME
        ttk.Button(self.left_frame, text=" Raporu Dosyaya Aktır (.txt)", command=self.export_report).pack(fill=tk.X, pady=2)
        ttk.Button(self.left_frame, text=" İşlem Loglarını Kaydet (.log)", command=self.export_logs).pack(fill=tk.X, pady=2)

        ttk.Label(self.left_frame, text="Sistem Durum Logu:", font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(5, 2))
        self.log_text = tk.Text(self.left_frame, width=42, height=6, state='disabled')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.right_frame = ttk.Frame(self.root, padding="10")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.log("Sistem hazır.")
        self.draw_graph()

    def apply_theme(self):
        bg_color = "#1e1e1e" if self.is_dark_mode else "#f0f0f0"
        fg_color = "#ffffff" if self.is_dark_mode else "#000000"
        
        self.root.configure(bg=bg_color)
        self.style.theme_use('clam')
        self.style.configure('.', background=bg_color, foreground=fg_color)
        self.style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        self.style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)
        self.style.configure('TLabel', background=bg_color, foreground=fg_color)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.theme_btn.config(text="☀️ Light Mode" if self.is_dark_mode else "🌙 Dark Mode")
        self.apply_theme()
        
        log_bg = "#2d2d2d" if self.is_dark_mode else "#f4f4f4"
        log_fg = "#00ffcc" if self.is_dark_mode else "#000000"
        self.log_text.config(bg=log_bg, fg=log_fg)
        
        self.draw_graph()

    def create_matrix_inputs(self):
        for widget in self.input_group.winfo_children():
            widget.destroy()

        res_labels = ", ".join([f"R{j}" for j in range(self.engine.num_resources)])
        ttk.Label(self.input_group, text=f"Alloc [{res_labels}] | Max Need | Prio | Cost", font=("Helvetica", 8, "bold")).pack(anchor=tk.W, pady=(0, 2))
        
        self.alloc_entries = []
        self.max_entries = []
        self.prio_entries = []
        self.cost_entries = []

        for i in range(self.engine.num_processes):
            row_frame = ttk.Frame(self.input_group)
            row_frame.pack(fill=tk.X, pady=1)
            ttk.Label(row_frame, text=f"P{i}:", width=3).pack(side=tk.LEFT)
            
            alloc_row = []
            for j in range(self.engine.num_resources):
                e = ttk.Entry(row_frame, width=3)
                e.insert(0, str(self.engine.allocation[i][j]))
                e.pack(side=tk.LEFT, padx=1)
                alloc_row.append(e)
            self.alloc_entries.append(alloc_row)

            ttk.Label(row_frame, text="|").pack(side=tk.LEFT, padx=1)

            max_row = []
            for j in range(self.engine.num_resources):
                e = ttk.Entry(row_frame, width=3)
                e.insert(0, str(self.engine.max_need[i][j]))
                e.pack(side=tk.LEFT, padx=1)
                max_row.append(e)
            self.max_entries.append(max_row)

            ttk.Label(row_frame, text="|").pack(side=tk.LEFT, padx=1)

            pe = ttk.Entry(row_frame, width=3)
            pe.insert(0, str(self.engine.priorities[i]))
            pe.pack(side=tk.LEFT, padx=1)
            self.prio_entries.append(pe)

            ce = ttk.Entry(row_frame, width=3)
            ce.insert(0, str(self.engine.costs[i]))
            ce.pack(side=tk.LEFT, padx=1)
            self.cost_entries.append(ce)

        ttk.Button(self.input_group, text="🔄 Matris Değerlerini Güncelle", command=self.update_values_from_ui).pack(fill=tk.X, pady=(6, 2))

    def update_health_badge(self):
        status_text, bg_color = self.engine.get_system_health_status()
        self.health_label.config(text=status_text, bg=bg_color)

    def load_preset(self):
        preset_name = self.preset_cb.get()
        self.engine.load_preset(preset_name)
        self.p_spin.set(str(self.engine.num_processes))
        self.r_spin.set(str(self.engine.num_resources))
        self.terminated_processes.clear()
        self.completed_processes.clear()
        self.create_matrix_inputs()
        self.draw_graph()
        self.log(f"Hazır Senaryo Yüklendi: {preset_name}")

    def apply_dimensions(self):
        try:
            new_p = int(self.p_spin.get())
            new_r = int(self.r_spin.get())
            self.engine.set_dimensions(new_p, new_r)
            self.terminated_processes.clear()
            self.completed_processes.clear()
            self.create_matrix_inputs()
            self.draw_graph()
            self.log(f"Sistem boyutu {new_p} Süreç x {new_r} Kaynak olarak güncellendi.")
        except ValueError:
            messagebox.showerror("Hata", "Lütfen geçerli tamsayılar girin!")

    def update_values_from_ui(self):
        try:
            for i in range(self.engine.num_processes):
                for j in range(self.engine.num_resources):
                    self.engine.allocation[i][j] = int(self.alloc_entries[i][j].get())
                    self.engine.max_need[i][j] = int(self.max_entries[i][j].get())
                self.engine.priorities[i] = int(self.prio_entries[i].get())
                self.engine.costs[i] = int(self.cost_entries[i].get())
            self.terminated_processes.clear()
            self.completed_processes.clear()
            self.log("Matris, Öncelik ve Maliyet değerleri güncellendi.")
            self.draw_graph()
            messagebox.showinfo("Başarılı", "Tüm değerler başarıyla güncellendi!")
        except ValueError:
            messagebox.showerror("Hata", "Lütfen kutulara geçerli tamsayılar girin!")

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"> {message}\n")
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def draw_graph(self, active_proc=None, active_status=None):
        self.ax.clear()
        
        bg_color = '#1e1e1e' if self.is_dark_mode else 'white'
        text_color = 'white' if self.is_dark_mode else 'black'
        self.fig.patch.set_facecolor(bg_color)
        self.ax.set_facecolor(bg_color)

        G = nx.DiGraph()
        processes = [f"P{i}" for i in range(self.engine.num_processes)]
        resources = [f"R{i}" for i in range(self.engine.num_resources)]

        G.add_nodes_from(processes)
        G.add_nodes_from(resources)

        edges = []
        edge_colors = []

        # Mavi Tahsis Okları
        for i in range(self.engine.num_processes):
            for j in range(self.engine.num_resources):
                if self.engine.allocation[i][j] > 0:
                    edges.append((f"R{j}", f"P{i}"))
                    edge_colors.append("#3498db")

        # Turuncu Talep Okları
        for i in range(self.engine.num_processes):
            for j in range(self.engine.num_resources):
                need = self.engine.max_need[i][j] - self.engine.allocation[i][j]
                if need > 0 and self.engine.available[j] < need:
                    edges.append((f"P{i}", f"R{j}"))
                    edge_colors.append("#e67e22")

        G.add_edges_from(edges)

        pos = {}
        for i, p in enumerate(processes):
            pos[p] = (i, 1)
        for j, r in enumerate(resources):
            pos[r] = (j * (max(len(processes)-1, 1) / max(len(resources)-1, 1)), 0)

        # RENK SKALASI: Kurban=Kırmızı, Tamamlanan=Yeşil, Kontrol Edilen=Sarı, Bekleyen=Mavi
        node_colors = []
        for p in processes:
            if p in self.terminated_processes:
                node_colors.append("#e74c3c")  # kırmızı (öldürülen kurban)
            elif p in self.completed_processes:
                node_colors.append("#2ecc71")  # yeşil (başarili)
            elif active_proc and p == active_proc:
                node_colors.append("#f1c40f")  # sarı (kontrol)
            else:
                node_colors.append("#a0c4ff")  # mavi (normal)

        nx.draw_networkx_nodes(G, pos, nodelist=processes, node_color=node_colors, node_size=1100, ax=self.ax)
        nx.draw_networkx_nodes(G, pos, nodelist=resources, node_color='#b9fbc0', node_shape='s', node_size=1100, ax=self.ax)
        nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", font_color='black', ax=self.ax)
        nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color=edge_colors, arrows=True, arrowsize=16, ax=self.ax)

        self.ax.set_title("Resource Allocation Graph (RAG)", fontsize=12, color=text_color)
        self.ax.axis('off')
        self.canvas.draw()
        
        self.update_health_badge()

    # --- SADECE SEÇİLEN STRATEJİYE UYAN TEK SÜRECİ ÖLDÜREN BUTON İŞLEVİ ---
    def resolve_single_victim_manual(self):
        selected_strategy = self.strategy_cb.get()
        victim_idx, exec_time_ms = self.engine.kill_exact_single_victim(selected_strategy, self.terminated_processes)
        
        if victim_idx is None:
            messagebox.showwarning("Uyarı", "Sistemde kapatılacak aktif süreç kalmadı!")
            return

        victim_name = f"P{victim_idx}"
        self.terminated_processes.add(victim_name)
        
        self.update_matrix_entries_from_engine()
        self.timer_label.config(text=f"{exec_time_ms} ms", fg="#2ecc71")
        self.draw_graph()
        
        self.log(f"MÜDAHALE ({selected_strategy}): {victim_name} kurban edildi ve kapatıldı (KIRMIZI). Diğer kilitli süreçler korundu!")
        messagebox.showinfo("Kurban Kapatıldı", 
                            f"Kurban Edilen Süreç: {victim_name} ({selected_strategy})\n\n"
                            f"Sadece {victim_name} sürecinin kaynakları geri alındı ve okları silindi.\n"
                            f"Diğer süreçlerin kilitlenmeleri ve okları aynen korunuyor!\n\n"
                            f"Hesaplama Süresi: {exec_time_ms} ms")

    # --- ADIM ADIM TÜM KİLİTLERİ ÇÖZEN ANİMASYON DÖNGÜSÜ ---
    def start_sequential_solution_animation(self):
        strategy = self.strategy_cb.get()
        self.anim_steps = self.engine.generate_sequential_resolve_steps(strategy)
        self.current_step_idx = 0
        self.completed_processes.clear()
        self.terminated_processes.clear()
        self.is_animating = True
        
        self.start_timer = time.time()
        self.timer_running = True
        self.update_timer()
        
        self.log(f"Sıralı Çözüm Başlatıldı (Strateji: {strategy})...")
        self.run_animation_loop()

    def update_timer(self):
        if self.timer_running:
            self.elapsed_time = time.time() - self.start_timer
            ms = round(self.elapsed_time * 1000, 1)
            self.timer_label.config(text=f"{self.elapsed_time:.3f} s ({ms} ms)", fg="#3498db")
            self.root.after(50, self.update_timer)

    def run_animation_loop(self):
        if not self.is_animating:
            return

        if self.current_step_idx < len(self.anim_steps):
            step = self.anim_steps[self.current_step_idx]
            self.log(step["msg"])

            if step["action"] == "CHECK":
                self.draw_graph(active_proc=step["process"], active_status="CHECK")
            elif step["action"] == "BLOCKED":
                self.draw_graph(active_proc=step["process"], active_status="BLOCKED")
            elif step["action"] == "RESOLVED":
                self.engine.allocation = step["new_alloc"]
                self.engine.max_need = step["new_max"]
                self.engine.available = step["new_avail"]
                self.update_matrix_entries_from_engine()
                self.draw_graph(active_proc=step["process"], active_status="CHECK")
            elif step["action"] == "SUCCESS":
                self.engine.allocation = step["new_alloc"]
                self.engine.max_need = step["new_max"]
                self.engine.available = step["new_avail"]
                self.update_matrix_entries_from_engine()
                self.completed_processes.add(step["process"])
                self.draw_graph()

            self.current_step_idx += 1
            self.root.after(self.anim_speed_ms, self.run_animation_loop)
        else:
            self.is_animating = False
            self.timer_running = False
            ms = round(self.elapsed_time * 1000, 2)
            self.timer_label.config(text=f"{self.elapsed_time:.3f} s ({ms} ms)", fg="#2ecc71")
            
            self.log(f"Tüm kilitlenmeler sırayla açıldı!")
            messagebox.showinfo("Çözüm Tamamlandı!", f"Tüm süreçler sırayla çözüldü!\n⏱️ Geçen Süre: {self.elapsed_time:.3f} s ({ms} ms)")

    def update_matrix_entries_from_engine(self):
        for i in range(self.engine.num_processes):
            for j in range(self.engine.num_resources):
                self.alloc_entries[i][j].delete(0, tk.END)
                self.alloc_entries[i][j].insert(0, str(self.engine.allocation[i][j]))
                self.max_entries[i][j].delete(0, tk.END)
                self.max_entries[i][j].insert(0, str(self.engine.max_need[i][j]))

    def export_report(self):
        is_safe, safe_seq = self.engine.run_bankers()
        report_text = self.engine.generate_report(is_safe, safe_seq)
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            messagebox.showinfo("Başarılı", "Rapor kaydedildi!")

    def export_logs(self):
        log_content = self.log_text.get("1.0", tk.END)
        file_path = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log Files", "*.log")])
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(log_content)
            messagebox.showinfo("Başarılı", "Loglar kaydedildi!")
