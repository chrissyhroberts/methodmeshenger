"""Small laptop chat GUI for a MethodMeshenger USB-connected ESP node."""

from __future__ import annotations

import base64
import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import serial
from serial.tools import list_ports


class ChatApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MethodMeshenger")
        self.geometry("620x620")
        self.minsize(420, 480)
        self.serial: serial.Serial | None = None
        self.events: queue.Queue[str] = queue.Queue()
        self.build_ui()
        self.refresh_ports()
        self.after(100, self.consume_events)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="MethodMeshenger", font=("TkDefaultFont", 22, "bold")).pack(anchor="w")
        ttk.Label(root, text="USB desktop chat for your ESP-NOW node").pack(anchor="w", pady=(2, 14))
        connection = ttk.Frame(root)
        connection.pack(fill="x")
        self.port = tk.StringVar()
        self.port_box = ttk.Combobox(connection, textvariable=self.port, state="readonly")
        self.port_box.pack(side="left", fill="x", expand=True)
        ttk.Button(connection, text="Refresh", command=self.refresh_ports).pack(side="left", padx=6)
        self.connect_button = ttk.Button(connection, text="Connect", command=self.toggle_connection)
        self.connect_button.pack(side="left")
        self.status = tk.StringVar(value="Not connected")
        ttk.Label(root, textvariable=self.status).pack(anchor="w", pady=(8, 8))
        self.messages = tk.Text(root, state="disabled", wrap="word", height=18)
        self.messages.pack(fill="both", expand=True)
        ttk.Label(root, text="Node diagnostics").pack(anchor="w", pady=(10, 2))
        self.diagnostics = tk.Text(root, state="disabled", wrap="none", height=7)
        self.diagnostics.pack(fill="x")
        composer = ttk.Frame(root)
        composer.pack(fill="x", pady=(10, 0))
        self.input = ttk.Entry(composer)
        self.input.pack(side="left", fill="x", expand=True)
        self.input.bind("<Return>", lambda _event: self.send())
        self.send_button = ttk.Button(composer, text="Send", command=self.send, state="disabled")
        self.send_button.pack(side="left", padx=(8, 0))

    def refresh_ports(self) -> None:
        ports = [item.device for item in list_ports.comports()]
        self.port_box["values"] = ports
        if ports and self.port.get() not in ports:
            self.port.set(ports[0])

    def toggle_connection(self) -> None:
        if self.serial is not None:
            self.close_serial()
            return
        if not self.port.get():
            messagebox.showinfo("Choose a node", "Connect an ESP board and choose its USB serial port.")
            return
        try:
            self.serial = serial.Serial(self.port.get(), 115200, timeout=0.25)
        except serial.SerialException as error:
            messagebox.showerror("Connection failed", str(error))
            return
        self.connect_button.configure(text="Disconnect")
        self.send_button.configure(state="normal")
        self.status.set("Connected")
        threading.Thread(target=self.read_loop, daemon=True).start()

    def read_loop(self) -> None:
        assert self.serial is not None
        while self.serial is not None and self.serial.is_open:
            line = self.serial.readline()
            if line:
                self.events.put(line.decode("utf-8", errors="replace").strip())

    def consume_events(self) -> None:
        while True:
            try:
                line = self.events.get_nowait()
            except queue.Empty:
                break
            self.handle_event(line)
        self.after(100, self.consume_events)

    def handle_event(self, line: str) -> None:
        self.diagnostics.configure(state="normal")
        self.diagnostics.insert("end", line + "\n")
        self.diagnostics.see("end")
        self.diagnostics.configure(state="disabled")
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self.status.set(line)
            return
        if event.get("event") == "message":
            frame = event.get("frame", {})
            self.status.set(f"Message from {frame.get('sender', 'node')}")
            self.append_message(str(frame.get("sender", "node")), str(frame.get("payload", "")))
        elif event.get("event") == "ack_received":
            self.status.set("Message delivered to the radio peer")
        elif event.get("event") == "ready":
            self.status.set(f"Connected · {event.get('node_id', 'node')}")
        elif event.get("event") == "error":
            self.status.set(f"Node error: {event.get('detail', 'unknown error')}")

    def append_message(self, sender: str, payload: str) -> None:
        self.messages.configure(state="normal")
        self.messages.insert("end", f"{sender}: {payload}\n")
        self.messages.see("end")
        self.messages.configure(state="disabled")

    def send(self) -> None:
        if self.serial is None or not self.serial.is_open:
            return
        text = self.input.get()
        if not text.strip():
            return
        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
        frame = {"methodmeshenger_serial": 1, "encoding": "utf-8", "payload_b64": encoded}
        try:
            self.serial.write((json.dumps(frame, separators=(",", ":")) + "\n").encode("ascii"))
        except serial.SerialException as error:
            self.status.set(f"Send failed: {error}")
            return
        self.append_message("You", text)
        self.input.delete(0, "end")

    def close_serial(self) -> None:
        if self.serial is not None:
            self.serial.close()
        self.serial = None
        self.connect_button.configure(text="Connect")
        self.send_button.configure(state="disabled")
        self.status.set("Not connected")

    def close(self) -> None:
        self.close_serial()
        self.destroy()


if __name__ == "__main__":
    ChatApp().mainloop()
