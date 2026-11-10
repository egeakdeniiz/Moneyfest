import datetime
import time

class DeadlockEngine:
    def __init__(self, num_processes=3, num_resources=2):
        self.num_processes = num_processes
        self.num_resources = num_resources
        
        self.allocation = [[1, 0], [0, 1], [1, 1]]
        self.max_need = [[2, 1], [1, 2], [1, 1]]
        self.available = [0, 0]
        
        self.priorities = [1, 2, 3]
        self.costs = [10, 20, 5]

    def reset_to_default(self):
        self.num_processes = 3
        self.num_resources = 2
        self.allocation = [[1, 0], [0, 1], [1, 1]]
        self.max_need = [[2, 1], [1, 2], [1, 1]]
        self.available = [0, 0]
        self.priorities = [1, 2, 3]
        self.costs = [10, 20, 5]

    def load_preset(self, preset_name):
        if preset_name == "Deadlock (Kilitlenme Senaryosu)":
            self.set_dimensions(3, 2)
            self.allocation = [[1, 0], [0, 1], [1, 1]]
            self.max_need = [[2, 1], [1, 2], [1, 1]]
            self.available = [0, 0]
            self.priorities = [1, 2, 3]
            self.costs = [10, 20, 5]
        elif preset_name == "Safe State (Güvenli Senaryo)":
            self.set_dimensions(3, 2)
            self.allocation = [[1, 0], [0, 1], [1, 0]]
            self.max_need = [[2, 1], [1, 1], [1, 1]]
            self.available = [1, 1]
            self.priorities = [1, 2, 3]
            self.costs = [10, 15, 20]
        elif preset_name == "High Starvation (Kaynak Açlığı)":
            self.set_dimensions(4, 2)
            self.allocation = [[2, 0], [0, 2], [1, 1], [0, 0]]
            self.max_need = [[3, 1], [1, 3], [2, 2], [4, 4]]
            self.available = [0, 0]
            self.priorities = [1, 4, 2, 3]
            self.costs = [50, 10, 30, 5]

    def set_dimensions(self, new_p, new_r):
        self.num_processes = new_p
        self.num_resources = new_r
        self.allocation = [[0 for _ in range(new_r)] for _ in range(new_p)]
        self.max_need = [[0 for _ in range(new_r)] for _ in range(new_p)]
        self.available = [0 for _ in range(new_r)]
        self.priorities = [i + 1 for i in range(new_p)]
        self.costs = [(i + 1) * 10 for i in range(new_p)]

    def run_bankers(self):
        work = list(self.available)
        finish = [False] * self.num_processes
        safe_sequence = []

        need = [
            [self.max_need[i][j] - self.allocation[i][j] for j in range(self.num_resources)]
            for i in range(self.num_processes)
        ]

        while len(safe_sequence) < self.num_processes:
            found = False
            for i in range(self.num_processes):
                if not finish[i]:
                    if all(need[i][j] <= work[j] for j in range(self.num_resources)):
                        for j in range(self.num_resources):
                            work[j] += self.allocation[i][j]
                        finish[i] = True
                        safe_sequence.append(f"P{i}")
                        found = True
                        break
            if not found:
                break

        is_safe = len(safe_sequence) == self.num_processes
        return is_safe, safe_sequence

    def get_system_health_status(self):
        is_safe, _ = self.run_bankers()
        if is_safe:
            return "HEALTHY", "#2ecc71"
        
        has_waiting_requests = False
        for i in range(self.num_processes):
            for j in range(self.num_resources):
                need = self.max_need[i][j] - self.allocation[i][j]
                if need > 0 and self.available[j] < need:
                    has_waiting_requests = True
                    break
        
        if has_waiting_requests:
            return "CRITICAL (DEADLOCK)", "#e74c3c"
        return "WARNING", "#f1c40f"

    def kill_exact_single_victim(self, strategy, terminated_set):
        """SADECE seçilen stratejiye uyan TEK kurbanı öldürür. Diğer hiçbir sürece dokunmaz."""
        start_time = time.perf_counter()
        
        # Henüz kapatılmamış süreçlerin indeksleri
        active_indices = [k for k in range(self.num_processes) if f"P{k}" not in terminated_set]
        if not active_indices:
            return None, 0.0

        if strategy == "Lowest Priority (En Düşük Öncelikliyi Öldür)":
            # Prio değeri en büyük olan = Önceliği en düşük demektir
            victim_idx = max(active_indices, key=lambda k: self.priorities[k])
        elif strategy == "Lowest Termination Cost (En Az Maliyetliyi Kurban Et)":
            # Cost değeri en küçük olan
            victim_idx = min(active_indices, key=lambda k: self.costs[k])
        elif strategy == "Victim: Max Allocation (En Çok Kaynak Tüketen)":
            # Allocation toplamı en çok olan
            victim_idx = max(active_indices, key=lambda k: sum(self.allocation[k]))
        else: # Resource Preemption
            victim_idx = active_indices[-1]

        # SADECE O KURBANIN KAYNAKLARINI SIFIRLA VE HAVUZA AKTAR
        for j in range(self.num_resources):
            self.available[j] += self.allocation[victim_idx][j]
            self.allocation[victim_idx][j] = 0
            self.max_need[victim_idx][j] = 0  # Talebi silinir

        end_time = time.perf_counter()
        exec_time_ms = round((end_time - start_time) * 1000, 4)

        return victim_idx, exec_time_ms

    def generate_sequential_resolve_steps(self, strategy):
        steps = []
        curr_alloc = [row[:] for row in self.allocation]
        curr_max = [row[:] for row in self.max_need]
        curr_avail = list(self.available)
        resolved_count = 0
        terminated_processes = set()

        for i in range(self.num_processes):
            proc_name = f"P{i}"
            if i in terminated_processes:
                continue

            need = [curr_max[i][j] - curr_alloc[i][j] for j in range(self.num_resources)]

            steps.append({
                "action": "CHECK",
                "process": proc_name,
                "msg": f"{proc_name} kontrol ediliyor... İhtiyaç: {need}, Kullanılabilir: {curr_avail}"
            })

            if not all(need[j] <= curr_avail[j] for j in range(self.num_resources)):
                resolved_count += 1
                active_indices = [k for k in range(self.num_processes) if k not in terminated_processes]
                
                if strategy == "Victim: Max Allocation (En Çok Kaynak Tüketen)":
                    victim_idx = max(active_indices, key=lambda k: sum(curr_alloc[k]))
                elif strategy == "Lowest Priority (En Düşük Öncelikliyi Öldür)":
                    victim_idx = max(active_indices, key=lambda k: self.priorities[k])
                elif strategy == "Lowest Termination Cost (En Az Maliyetliyi Kurban Et)":
                    victim_idx = min(active_indices, key=lambda k: self.costs[k])
                else:
                    victim_idx = active_indices[-1]

                steps.append({
                    "action": "BLOCKED",
                    "process": proc_name,
                    "victim": f"P{victim_idx}",
                    "msg": f"⚠️ {proc_name} kilitlendi! P{victim_idx} kurban seçilip kapatılıyor..."
                })

                for j in range(self.num_resources):
                    curr_avail[j] += curr_alloc[victim_idx][j]
                    curr_alloc[victim_idx][j] = 0
                    curr_max[victim_idx][j] = 0
                
                terminated_processes.add(victim_idx)

                steps.append({
                    "action": "RESOLVED",
                    "process": proc_name,
                    "new_alloc": [row[:] for row in curr_alloc],
                    "new_max": [row[:] for row in curr_max],
                    "new_avail": list(curr_avail),
                    "msg": f"⚡ P{victim_idx} kapatılarak kaynaklar serbest bırakıldı!"
                })

                need = [curr_max[i][j] - curr_alloc[i][j] for j in range(self.num_resources)]
                if all(need[j] <= curr_avail[j] for j in range(self.num_resources)):
                    for j in range(self.num_resources):
                        curr_avail[j] += curr_alloc[i][j]
                        curr_alloc[i][j] = 0
                        curr_max[i][j] = 0
                    
                    steps.append({
                        "action": "SUCCESS",
                        "process": proc_name,
                        "new_alloc": [row[:] for row in curr_alloc],
                        "new_max": [row[:] for row in curr_max],
                        "new_avail": list(curr_avail),
                        "resolved_count": resolved_count,
                        "msg": f"✅ {proc_name} serbest kalan kaynaklarla tamamlandı!"
                    })
            else:
                for j in range(self.num_resources):
                    curr_avail[j] += curr_alloc[i][j]
                    curr_alloc[i][j] = 0
                    curr_max[i][j] = 0

                steps.append({
                    "action": "SUCCESS",
                    "process": proc_name,
                    "new_alloc": [row[:] for row in curr_alloc],
                    "new_max": [row[:] for row in curr_max],
                    "new_avail": list(curr_avail),
                    "resolved_count": resolved_count,
                    "msg": f"✅ {proc_name} tamamlandı."
                })

        return steps

    def generate_report(self, is_safe, safe_seq):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = f"=========================================\n"
        report += f" DEADLOCK SIMULATOR - SISTEM DURUM RAPORU\n"
        report += f" Tarih: {now}\n"
        report += f"=========================================\n\n"
        report += f"Sistem Boyutu: {self.num_processes} Süreç (P), {self.num_resources} Kaynak (R)\n\n"
        report += "SÜREÇ ÖNCELİKLERİ VE MALİYETLERİ:\n"
        for i in range(self.num_processes):
            report += f"  P{i}: Priority={self.priorities[i]}, Cost={self.costs[i]}\n"
        report += "\nALLOCATION MATRISI:\n"
        for i, row in enumerate(self.allocation):
            report += f"  P{i}: {row}\n"
        report += "\nMAX NEED MATRISI:\n"
        for i, row in enumerate(self.max_need):
            report += f"  P{i}: {row}\n"
        report += f"\nAVAILABLE VECTOR: {self.available}\n"
        report += "-----------------------------------------\n"
        if is_safe:
            report += f"GÜVENLİK DURUMU: GÜVENLİ (SAFE)\n"
            report += f"Güvenli Dizi (Safe Sequence): {' -> '.join(safe_seq)}\n"
        else:
            report += f"GÜVENLİK DURUMU: GÜVENSİZ / DEADLOCK RISKI!\n"
        report += "=========================================\n"
        return report
