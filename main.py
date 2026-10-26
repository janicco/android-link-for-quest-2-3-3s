import socket
import struct
import threading
import cv2
import numpy as np
import customtkinter as ctk
from mss import mss

# Modernes Design (Dark Mode) für die App
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class VRStreamApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fenster-Einstellungen
        self.title("VR Streamer - PC Server App")
        self.geometry("600x520")
        self.resizable(False, False)

        self.is_streaming = False
        self.server_thread = None

        # --- Oberflächen-Elemente (GUI) ---
        
        # Titel
        self.title_label = ctk.CTkLabel(self, text="Meta Quest PC-Streamer", font=ctk.CTkFont(size=22, weight="bold"))
        self.title_label.pack(pady=20)

        # IP-Anzeige Box
        self.ip_frame = ctk.CTkFrame(self)
        self.ip_frame.pack(fill="x", padx=25, pady=10)

        self.ip_label = ctk.CTkLabel(self.ip_frame, text=f"Deine lokale IP / Hotspot-IP:\n{self.get_local_ip()}", font=ctk.CTkFont(size=15, weight="bold"))
        self.ip_label.pack(pady=12, padx=10)

        # Steuerung Buttons (Start / Stop)
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=20)

        self.start_btn = ctk.CTkButton(self.btn_frame, text="Stream Starten", fg_color="#28a745", hover_color="#218838", command=self.start_server, width=160, height=45, font=ctk.CTkFont(size=15, weight="bold"))
        self.start_btn.pack(side="left", padx=15)

        self.stop_btn = ctk.CTkButton(self.btn_frame, text="Stream Stoppen", fg_color="#dc3545", hover_color="#c82333", command=self.stop_server, width=160, height=45, font=ctk.CTkFont(size=15, weight="bold"), state="disabled")
        self.stop_btn.pack(side="left", padx=15)

        # Status & Log Protokoll (Live-Anzeige unten im Fenster)
        self.log_box = ctk.CTkTextbox(self, width=550, height=160, font=ctk.CTkFont(size=12))
        self.log_box.pack(pady=10)
        self.log("App bereit. Klicke auf 'Stream Starten', um den Server zu aktivieren.")

    def get_local_ip(self):
        """Ermittelt automatisch die IP im WLAN oder Handy-Hotspot"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def log(self, message):
        """Fügt Text zum Statusfenster hinzu"""
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")

    def start_server(self):
        if not self.is_streaming:
            self.is_streaming = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            
            # Server läuft in einem Hintergrund-Thread, damit das Fenster nicht einfriert!
            self.server_thread = threading.Thread(target=self.run_streaming_server, daemon=True)
            self.server_thread.start()

    def stop_server(self):
        self.is_streaming = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.log("[INFO] Stream wurde manuell gestoppt.")

    def run_streaming_server(self):
        HOST = '0.0.0.0'
        PORT = 5000

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(1)

            self.log(f"[SERVER] Gestartet auf Port {PORT}. Warte auf Verbindung...")
            self.server_socket.settimeout(1.0)

            conn = None
            while self.is_streaming:
                try:
                    conn, addr = self.server_socket.accept()
                    break
                except socket.timeout:
                    continue

            if not self.is_streaming:
                if conn: conn.close()
                self.server_socket.close()
                return

            self.log(f"[VERBUNDEN] Client hat sich verbunden: {addr[0]}")

            with mss() as sct:
                monitor = sct.monitors[1]  # Hauptbildschirm aufnehmen
                while self.is_streaming:
                    # 1. Bildschirm abgreifen
                    img = np.array(sct.grab(monitor))
                    
                    # 2. Auf 720p verkleinern für flüssigen Stream
                    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    frame = cv2.resize(frame, (1280, 720))

                    # 3. Komprimieren
                    _, encoded_image = cv2.imencode('.jpg', frame, [cv2.imencode_param('IMWRITE_JPEG_QUALITY', 70)])
                    data = encoded_image.tobytes()

                    # 4. Senden
                    size = len(data)
                    conn.sendall(struct.pack(">L", size) + data)

            if conn:
                conn.close()
            self.server_socket.close()
            self.log("[SERVER] Verbindung getrennt.")

        except Exception as e:
            self.log(f"[FEHLER] {e}")
            self.is_streaming = False
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

if __name__ == "__main__":
    app = VRStreamApp()
    app.mainloop()
