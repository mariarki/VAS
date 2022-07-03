import datetime
import random
import sys
import time
from argparse import ArgumentParser
from ssl import ALERT_DESCRIPTION_UNRECOGNIZED_NAME

import spade
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message

mojeKarte = []
polozeneKarte = []
suparnici = []

class Suparnik:
    def __init__(self, ime):
        self.ime = ime
        self.imaKarte = set()
        self.nemaKarte = set()
        self.mozeIgrati = True
class KartaPoanvljanje:
    def __init__(self, karta, ponavljanje):
        self.karta = karta
        self.ponavljanje = ponavljanje

    def __eq__(self, other):
        return self.ponavljanje == other.ponavljanje
    
    def __lt__(self, other):
        return self.ponavljanje < other.ponavljanje

def odaberiKartu():
    popisKarata = []
    global mojeKarte
    global suparnici

    for karta in set(mojeKarte):
        popisKarata.append(KartaPoanvljanje(karta, mojeKarte.count(karta)))


    popisKarata = sorted(popisKarata, reverse = True)

    for karta in popisKarata:
        for suparnik in suparnici:
            if karta.karta in suparnik.imaKarte and suparnik.mozeIgrati == True:
                return suparnik.ime, karta.karta
        
    for karta in popisKarata:
        for suparnik in suparnici:
            if karta.karta not in suparnik.nemaKarte and suparnik.mozeIgrati == True:
                return suparnik.ime, karta.karta

    while True:
        suparnik = suparnici[random.randint(0,2)]
        if suparnik.mozeIgrati == True:
            return suparnici[random.randint(0,2)].ime, popisKarata[0].karta


class Igrac(Agent):
    def __init__(self, *args, igrac, **kwargs):
        super().__init__(*args, **kwargs)
        self.igrac = igrac
        
    class PonasanjeIgraca(FSMBehaviour):
        async def on_start(self):
            print(f"Usao sam u igru...")

        async def on_end(self):
            await self.agent.stop()

    class PridruziSeIgri(State):
        async def run(self):
            poruka = {
                "vrsta": "pridruzi_se",
                "igrac": agentIgraca,
            }

            p = Message(
                to = "gofish@localhost",
                body = str(poruka),
            )

            await self.send(p)

            self.set_next_state("cekanje_igre")

    class CekajIgru(State):
        async def run(self):
            print("Cekam igru...")
            
            poruka = await self.receive(timeout = 180)
            global mojeKarte

            if(poruka):
                sadrzajPoruke = eval(poruka.body)

                if sadrzajPoruke["vrsta"] == "tvoje_karte":
                    mojeKarte = sadrzajPoruke["karte"]
                    print("Moje karte su: " )
                    print(mojeKarte)

                elif sadrzajPoruke["vrsta"] == "tvoj_suparnik":
                    suparnici.append(Suparnik(sadrzajPoruke["suparnik"]))

                if len(suparnici) == 3:
                    self.set_next_state("igranje_igre")
                else:
                    self.set_next_state("cekanje_igre")
            else:
                self.set_next_state("cekanje_igre")

    class IgranjeIgre(State):
        
        async def run(self):
            poruka = await self.receive(timeout = 180)
            global mojeKarte
            global suparnici
            
            if poruka:
                sadrzajPoruke = eval(poruka.body)
                vrstaPoruke = sadrzajPoruke["vrsta"]

                if vrstaPoruke == "tvoj_red":
                    kartaOd, karta = odaberiKartu()
                  
                    poruka = {
                        "karta" : karta,
                        "kartaOd" : kartaOd
                    }

                    p = Message(
                        to = "gofish@localhost",
                        body = str(poruka)
                    )

                    await self.send(p)

                elif vrstaPoruke == "daj_kartu":
        
                    karta = int(sadrzajPoruke["karta"])
                    if karta in mojeKarte:
                        poruka = {
                            "vrsta" : "imam_kartu",
                            "karta" : karta,
                            "broj_karata" : mojeKarte.count(karta)
                        }
                    else:
                        poruka = {
                            "vrsta" : "go_fish",
                            "karta" : karta
                        }

                    p = Message(
                        to = "gofish@localhost",
                        body = str(poruka)
                    )

                    await self.send(p)
                
                elif vrstaPoruke == "tvoje_karte":
                    #print("Uso u tvoje karte")
                    mojeKarte = sadrzajPoruke["karte"]
                
                elif vrstaPoruke == "karte_suparnika":
                    #print("Uso u karte suparnika")
                    imeSuparnika = sadrzajPoruke["imeSuparnika"]
                    imaKarte = sadrzajPoruke["imaKarte"]
                    nemaKarte = sadrzajPoruke["nemaKarte"]
                    mozeIgrati = sadrzajPoruke["mozeIgrati"]

                    for suparnik in suparnici:
                        if suparnik.ime == imeSuparnika:
                            suparnik.imaKarte = imaKarte
                            suparnik.nemaKarte = nemaKarte
                            suparnik.mozeIgrati = mozeIgrati

                elif vrstaPoruke == "kraj":
                    self.set_next_state("kraj_igre")
                    return
            self.set_next_state("igranje_igre")

    class KrajIgre(State):
        async def run(self):
            print("Igra je gotova...")

    async def setup(self):
        ponasanjeIgraca = self.PonasanjeIgraca()

        ponasanjeIgraca.add_state(name="pridruzi_se", state=self.PridruziSeIgri(), initial=True)
        ponasanjeIgraca.add_state(name="cekanje_igre", state=self.CekajIgru())
        ponasanjeIgraca.add_state(name = "igranje_igre", state = self.IgranjeIgre())
        ponasanjeIgraca.add_state(name = "kraj_igre", state = self.KrajIgre())

        ponasanjeIgraca.add_transition(source="pridruzi_se", dest="cekanje_igre")
        ponasanjeIgraca.add_transition(source="cekanje_igre", dest="cekanje_igre")
        ponasanjeIgraca.add_transition(source="cekanje_igre", dest="igranje_igre")
        ponasanjeIgraca.add_transition(source="igranje_igre", dest="igranje_igre")
        ponasanjeIgraca.add_transition(source="igranje_igre", dest="kraj_igre")


        self.add_behaviour(ponasanjeIgraca)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-ime", type = str, help = "Ime igraca.")
    args = parser.parse_args()

    imeIgraca = args.ime
    agentIgraca = f"{imeIgraca}@localhost"

    player = Igrac(agentIgraca, "password", igrac=agentIgraca)
    playerKraj = player.start()
    playerKraj.result()

    while player.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    player.stop()

    spade.quit_spade()