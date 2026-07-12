from scapy.all import sniff

def iniciar_sniffer(parar_evento):
    # O stop_filter é o segredo para o Scapy parar sem travar a thread
    sniff(iface="ens33", stop_filter=lambda x: parar_evento.is_set(), store=0)
