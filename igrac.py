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

class Karta:
    def __init__(self, oznaka, broj):
        self.oznaka = str(oznaka)
        self.broj = str(broj)

    def __str__(self):
        return self.oznaka  + self.broj

    def __repr__(self):
        return self.oznaka + self.broj

def PorukaUKarte(poruka):
    poruka = poruka[1:-1]
    poruka = poruka.split(',')

    poruke = []

    for p in poruka:
        a = p.strip()
        poruke.append(Karta(a[0], a[1]))
    return poruke

def OdbacivanjeKarata(karteIgraca):
    slova = [[] for i in range(5)]
    brojevi = [[] for i in range(5)]

    for karta in karteIgraca:
        slovo = karta.oznaka
        broj = karta.broj
        if slovo == "A":
            slova[0].append(karta)
        elif slovo == "B":
            slova[1].append(karta)
        elif slovo == "C":
            slova[2].append(karta)
        elif slovo == "D":
            slova[3].append(karta)
        elif slovo == "E":
            slova[4].append(karta)
        brojevi[int(broj) - 1].append(karta)

    slova.sort(key=lambda x: -len(x))
    brojevi.sort(key=lambda x: -len(x))

    if len(slova[0]) > len(brojevi[0]):
        zadrzati = slova[0]
    else:
        zadrzati = brojevi[0]

    for karta in karteIgraca:
        if karta not in zadrzati:
            return karta

class Igrac(Agent):
    def __init__(self, *args, igrac, **kwargs):
        super().__init__(*args, **kwargs)
        self.igrac = igrac

    class PonasanjeIgraca(FSMBehaviour):
        async def on_start(self):
            print(f"{self.agent.igrac} je ušao u igru!")

        async def on_end(self):
            print(f"{self.agent.igrac} je gotov s igrom!")

            await self.agent.stop()

    class PridruziSeIgri(State):
        async def run(self):
            poruka = {
                "vrsta": "pridruzi_se",
                "igrac": agentIgraca,
            }

            p = Message(
                to = "pogadanje@localhost",
                body = str(poruka),
            )

            await self.send(p)

            self.set_next_state("cekanje_igre")

    class CekajIgru(State):
        async def run(self):
            poruka = await self.receive(timeout=120)
            if poruka:
                karte = PorukaUKarte(poruka.body)
                print(f"Vase karte su... {karte}\n")
                self.set_next_state("trenutna_igra")
            else:
                self.set_next_state("cekanje_igre")

    class Igra(State):
        async def run(self):
            poruka = await self.receive(timeout=120)
            if poruka:
                sadrzaj = eval(poruka.body)
                status = sadrzaj["vrsta"]
                karte = PorukaUKarte(sadrzaj["karte"])

                if ("tvoj_red" in status):
                    print(f"Tvoj red za igranje, odaberi karte koje ces izbaciti...\n")
                    print(f"Moje karte su... {karte}")
                    kartaZaIzbacit = OdbacivanjeKarata(karte)
                    print(f"Izbacit cu... {kartaZaIzbacit} \n")
                    time.sleep(0.5)
                    poruka = Message(
                        to="pogadanje@localhost",
                        body=str(kartaZaIzbacit)
                    )
                    await self.send(poruka)
                    self.set_next_state("trenutna_igra")
                elif "pobjednik" in status:
                    print(f"Moje karte su... {karte}")
                    print("Ovaj puta sam imao više sreće!\n")
                    self.set_next_state("kraj_igre")

                elif "gubitnik" in status:
                    print(f"Moje karte su... {karte}")
                    print("Ahh, možda drugi put...\n")
                    self.set_next_state("kraj_igre")

                elif "izjednaceno" in status:
                    print(f"Moje karte su... {karte}")
                    print("Hah, koje su šanse...\n")
                    self.set_next_state("kraj_igre")

                else:
                    self.set_next_state("pridruzi_se")
            else:
                self.set_next_state("trenutna_igra")

    class KrajIgre(State):
        async def run(self):
            print("Kraj igre, bila je ovo dobra igra!\n")

    async def setup(self):
        stanja = self.PonasanjeIgraca()

        stanja.add_state(name="pridruzi_se", state=self.PridruziSeIgri(), initial=True)
        stanja.add_state(name="cekanje_igre", state=self.CekajIgru())
        stanja.add_state(name="trenutna_igra", state=self.Igra())
        stanja.add_state(name="kraj_igre", state=self.KrajIgre())

        stanja.add_transition(source="pridruzi_se", dest="cekanje_igre")
        stanja.add_transition(source="cekanje_igre", dest="cekanje_igre")
        stanja.add_transition(source="cekanje_igre", dest="trenutna_igra")
        stanja.add_transition(source="trenutna_igra", dest="trenutna_igra")
        stanja.add_transition(source="trenutna_igra", dest="kraj_igre")


        self.add_behaviour(stanja)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-ime", type = str, help = "Ime igraca")
    args = parser.parse_args()

    imeIgraca = args.ime
    agentIgraca = f"{imeIgraca}@localhost"

    igrac = Igrac(agentIgraca, "password", igrac=agentIgraca)
    playerKraj = igrac.start()
    playerKraj.result()

    while igrac.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    igrac.stop()

    spade.quit_spade()