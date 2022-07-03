import datetime
import pickle
import random
import time
import os

import spade
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message
from sqlalchemy import null

class Igrac:
    def __init__(self, ime):
        self.ime = ime
        self.karte = []
        self.imaKarte = set()
        self.nemaKarte = set()
        self.rezultat = 0
        self.mozeIgrati = True
    def __eq__(self, other):
        return self.rezultat == other.rezultat
    
    def __lt__(self, other):
        return self.rezultat < other.rezultat

igraci = []
karte = []
brojac = 0
trenutniIgrac = ""
zatraziOd = ""

for i in range(1,14):
    karte.append(i)
    karte.append(i)
    karte.append(i)
    karte.append(i)

class Server(Agent):
    class PonasanjeServera(FSMBehaviour):
        async def on_start(self):
            print(f"Pokrenut sam... Cekam igrace...")

        async def on_end(self):
            print(f"Gasim se...")
            await self.agent.stop()

    class CekanjeIgraca(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd
            poruka = await self.receive(timeout = 60)

            if poruka:
                sadrzajPoruke = eval(poruka.body)

                if(sadrzajPoruke["vrsta"] == "pridruzi_se"):
                    noviIgrac = Igrac(sadrzajPoruke["igrac"])
                    igraci.append(noviIgrac)
                    print(f"Igrac {len(igraci)} se pridruzio... {noviIgrac.ime}")

                else:
                    print(f"Nepoznat zahtjev...")
         
                if len(igraci) == 4:
                    print(f"Svi igraci su se pridruzili... Pocinjem igru za 2 sekunde...")
                    time.sleep(2)
                    self.set_next_state("pocetak_igre")

                else:
                    self.set_next_state("cekanje_igraca")

            else:
                self.set_next_state("cekanje_igraca")
    
    class PocetakIgre(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd
            print(f"Usao sam u pocetak igre... Krecem dijeliti karte...")
            for i in range(0,4):
                random.shuffle(karte)
                igraci[i].karte.append(karte.pop())
                igraci[i].karte.append(karte.pop())
                igraci[i].karte.append(karte.pop())
                igraci[i].karte.append(karte.pop())
                igraci[i].karte.append(karte.pop())
                igraci[i].karte.sort()
                
            for igrac in igraci:
                poruka = {
                    "vrsta" : "tvoje_karte",
                    "karte" : igrac.karte
                }
                
                p = Message(
                    to = igrac.ime,
                    body = str(poruka)
                )
                
                await self.send(p)
            
            for igrac in igraci:
                for suparnik in igraci:
                    if igrac.ime != suparnik.ime:
                        poruka = {
                            "vrsta" : "tvoj_suparnik",
                            "suparnik" : suparnik.ime
                        }

                        p = Message(
                            to = igrac.ime,
                            body = str(poruka)
                        )

                        await self.send(p)

            self.set_next_state("igranje_igre")

    class IgranjeIgre(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd

            if igraci[0].mozeIgrati == False and igraci[1].mozeIgrati == False and igraci[2].mozeIgrati == False and igraci[3].mozeIgrati == False:
                self.set_next_state("kraj_igre")
            else:
                self.set_next_state("javi_da_igra")

    class JaviDaIgra(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd

            if igraci[brojac].mozeIgrati == True:
                trenutniIgrac = igraci[brojac].ime
            else:
                brojac += 1
                if brojac == 4:
                    brojac = 0
                self.set_next_state("igranje_igre")
                return

            poruka = {
                "vrsta" : "tvoj_red"
            }
            
            p = Message(
                to = trenutniIgrac,
                body = str(poruka)
            )
            await self.send(p)

            self.set_next_state("zatrazi_kartu")

    class ZatraziKartu(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd
            
            poruka = await self.receive(timeout = 60)
            if poruka:
                sadrzajPoruke = eval(poruka.body)
               
                karta = sadrzajPoruke["karta"]
                zatraziOd = sadrzajPoruke["kartaOd"]
                
                clear = lambda: os.system('clear')
                clear()
                print(f"{trenutniIgrac} trazi od {zatraziOd} kartu {karta}")
                print("")
                print("Karte igraca: ")
                print("-------------------------")
                for igrac in igraci:
                    print(f"{igrac.ime} - {sorted(igrac.karte)}")
                print("")
                print("Znanje igraca: ")
                print("-------------------------")
                for igrac in igraci:
                    print(f"{igrac.ime} ima karte: {igrac.imaKarte}")
                    print(f"{igrac.ime} nema karte: {igrac.nemaKarte}")
                print("")
                print("Trenutno stanje: ")
                print("-------------------------")
                for igrac in igraci:
                    print(f"Igrac: {igrac.ime} ima: {igrac.rezultat} bodova!")
                
                poruka = {
                    "vrsta" : "daj_kartu",
                    "karta" : karta
                }

                p = Message(
                    to = zatraziOd,
                    body = str(poruka)
                )
                await self.send(p)
                self.set_next_state("odgovor_igraca")

            else:
                self.set_next_state("zatrazi_kartu")

    class OdgovorIgraca(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd
            poruka = await self.receive(timeout = 60)
            if poruka:
                sadrzajPoruke = eval(poruka.body)
                vrstaPoruke = sadrzajPoruke["vrsta"]
                
                if vrstaPoruke == "imam_kartu":
                    brojKarata = sadrzajPoruke["broj_karata"]
                    karta = sadrzajPoruke["karta"]

 
                    for igrac in igraci:
                        if igrac.ime == zatraziOd:
                            igrac.nemaKarte.add(int(karta))
                            if int(karta) in igrac.imaKarte:
                                igrac.imaKarte.remove(int(karta))
                            for i in range (0, int(brojKarata)):
                                igrac.karte.remove(int(karta))

                        if igrac.ime == trenutniIgrac:
                            igrac.imaKarte.add(int(karta))
                            if int(karta) in igrac.nemaKarte:
                                igrac.nemaKarte.remove(int(karta))
                            for i in range (0, int(brojKarata)):
                                igrac.karte.append(int(karta))

                    self.set_next_state("provjeri_karte_igraca")

                elif vrstaPoruke == "go_fish":
                    karta = sadrzajPoruke["karta"]
                    for igrac in igraci:
                        if igrac.ime == trenutniIgrac:
                            if len(karte) != 0:
                                igrac.karte.append(karte.pop())
                        if igrac.ime == zatraziOd:
                            igrac.nemaKarte.add(int(karta))

                    brojac += 1
                    if brojac == 4:
                        brojac = 0
 
                    self.set_next_state("provjeri_karte_igraca")

    class ProvjeriKarteIgraca(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd
            for igrac in igraci:
                for karta in set(igrac.karte):
                    if igrac.karte.count(karta) == 4:
                        igrac.rezultat += 1
                        for i in range (0,4):
                            igrac.karte.remove(karta)

            for igrac in igraci:
                if len(igrac.karte) == 0:
                    if len(karte) < 5:
                        for j in range (0,len(karte)):
                            igrac.karte.append(karte.pop())
                    else:
                        for j in range(0,5):
                            igrac.karte.append(karte.pop())

            for igrac in igraci:
                if len(igrac.karte) == 0:
                    igrac.mozeIgrati = False

            self.set_next_state("informiraj_igrace")

    class InformirajIgrace(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd
                
            for igrac in igraci:          
                poruka = {
                    "vrsta" : "tvoje_karte",
                    "karte" : igrac.karte
                }

                p = Message(
                    to = igrac.ime,
                    body = str(poruka)
                )

                await self.send(p)

            for igrac in igraci:
                for suparnik in igraci:
                    if igrac.ime != suparnik.ime:
                        poruka = {
                            "vrsta" : "karte_suparnika",
                            "imeSuparnika" : suparnik.ime,
                            "imaKarte" : suparnik.imaKarte,
                            "nemaKarte" : suparnik.nemaKarte,
                            "mozeIgrati" : suparnik.mozeIgrati
                        }

                        p = Message(
                            to = igrac.ime,
                            body = str(poruka)
                        )

                        await self.send(p)           
            time.sleep(2)
            self.set_next_state("igranje_igre")

    class KrajIgre(State):
        async def run(self):
            global igraci
            global karte
            global brojac
            global trenutniIgrac
            global zatraziOd
            igraci = sorted(igraci, reverse = True)
            clear = lambda: os.system('clear')
            clear()
            print("")
            print("Zavrsno stanje: ")
            print("-------------------------")
            for igrac in igraci:
                print(f"Igrac: {igrac.ime} ima: {igrac.rezultat} bodova!")
            
            for igrac in igraci:
                poruka = {
                        "vrsta" : "kraj"
                    }

                p = Message(
                    to = igrac.ime,
                    body = str(poruka)
                )

                await self.send(p)


                            
    async def setup(self):
        ponasanjeServera = self.PonasanjeServera()

        ponasanjeServera.add_state(name = "cekanje_igraca", state = self.CekanjeIgraca(), initial = True)
        ponasanjeServera.add_state(name = "pocetak_igre", state = self.PocetakIgre())
        ponasanjeServera.add_state(name = "igranje_igre", state = self.IgranjeIgre())
        ponasanjeServera.add_state(name = "javi_da_igra", state = self.JaviDaIgra())
        ponasanjeServera.add_state(name = "zatrazi_kartu", state = self.ZatraziKartu())
        ponasanjeServera.add_state(name = "odgovor_igraca", state = self.OdgovorIgraca())
        ponasanjeServera.add_state(name = "provjeri_karte_igraca", state = self.ProvjeriKarteIgraca())
        ponasanjeServera.add_state(name = "informiraj_igrace", state = self.InformirajIgrace())
        ponasanjeServera.add_state(name = "kraj_igre", state = self.KrajIgre())

        ponasanjeServera.add_transition(source = "cekanje_igraca", dest = "cekanje_igraca")
        ponasanjeServera.add_transition(source = "cekanje_igraca", dest = "pocetak_igre")
        ponasanjeServera.add_transition(source = "pocetak_igre", dest = "igranje_igre")
        ponasanjeServera.add_transition(source = "igranje_igre", dest = "javi_da_igra")
        ponasanjeServera.add_transition(source = "igranje_igre", dest = "kraj_igre")
        ponasanjeServera.add_transition(source = "javi_da_igra", dest = "zatrazi_kartu")
        ponasanjeServera.add_transition(source = "javi_da_igra", dest = "igranje_igre")
        ponasanjeServera.add_transition(source = "zatrazi_kartu", dest = "zatrazi_kartu")
        ponasanjeServera.add_transition(source = "zatrazi_kartu", dest = "odgovor_igraca")
        ponasanjeServera.add_transition(source = "odgovor_igraca", dest = "provjeri_karte_igraca")
        ponasanjeServera.add_transition(source = "provjeri_karte_igraca", dest = "informiraj_igrace")
        ponasanjeServera.add_transition(source = "informiraj_igrace", dest = "igranje_igre")
        
        self.add_behaviour(ponasanjeServera)

if __name__ == '__main__':

    server = Server("gofish@localhost", "karte123")
  
    igra = server.start()

    igra.result()

    while server.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    server.stop()
    spade.quit_spade()