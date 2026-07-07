from scapy.all import sniff, TCP, UDP, IP
import os

LOG_FILE = "relatorios/sniffer_log.txt"

def pacote_callback(pacote):
    if pacote.haslayer(IP):
        camada = pacote[TCP] if pacote.haslayer(TCP) else (pacote[UDP] if pacote.haslayer(UDP) else None)
        if camada:
            src, dst = pacote[IP].src, pacote[IP].dst
            msg = f"[ALERTA] Tráfego detectado: {src} -> {dst}"
            print(msg)
            with open(LOG_FILE, "a") as f:
                f.write(msg + "\n")

def iniciar_sniffer(interface="ens33"):
    print(f"[*] Sniffer rodando em {interface}. Logs em {LOG_FILE}")
    sniff(iface=interface, filter="tcp or udp", prn=pacote_callback, store=0)
