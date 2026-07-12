from scapy.all import sniff, TCP, UDP, IP
import os

LOG_FILE = "relatorios/sniffer_log.txt"

def pacote_callback(pacote):
    if pacote.haslayer(IP):
        src, dst = pacote[IP].src, pacote[IP].dst
        msg = f"[ALERTA] Tráfego detectado: {src} -> {dst}"
        with open(LOG_FILE, "a") as f:
            f.write(msg + "\n")

# Mudamos o nome para forçar o Python a reconhecer a nova função
def iniciar_sniffer_v2(interface, parar_evento):
    print(f"[*] Sniffer v2 rodando em {interface}")
    
    sniff(
        iface=interface, 
        filter="tcp or udp", 
        prn=pacote_callback, 
        store=0,
        stop_filter=lambda x: parar_evento.is_set()
    )
