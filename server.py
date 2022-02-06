import datetime
import pickle
import random
import time

import spade
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message


class Igrac:
    def __init__(self, ime):
        self.ime = ime
        self.karte = []

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self.ime == other.ime and self.karte == other.karte

class Karta:
    def __init__(self, oznaka, broj):
        self.oznaka = str(oznaka)
        self.broj = str(broj)

    def __str__(self):
        return self.oznaka + self.broj

    def __repr__(self):
        return self.oznaka + self.broj

    def vrijednost(self):
        return int(self.oznaka, 16) + int(self.broj)

    def __eq__(self, other):
        return self.oznaka == other.oznaka and self.broj == other.broj

spilKarata = []

for i in range(1, 6):
    spilKarata.append(Karta("A", i))
    spilKarata.append(Karta("B", i))
    spilKarata.append(Karta("C", i))
    spilKarata.append(Karta("D", i))
    spilKarata.append(Karta("E", i))

igraci = []

def ZbrojiKarte(karteIgraca):
    zbroj = 0
    for karta in karteIgraca:
        zbroj += karta.vrijednost()
    return zbroj


def PronadiPobjednika(trenutniIgrac, drugiIgrac):
    slova = [[] for i in range(5)]
    brojevi = [[] for i in range(5)]

    for karta in trenutniIgrac.karte:
        slovo = karta.oznaka
        broj = karta.broj
        if (slovo == "A"):
            slova[0].append(karta)
        elif (slovo == "B"):
            slova[1].append(karta)
        elif (slovo == "C"):
            slova[2].append(karta)
        elif (slovo == "D"):
            slova[3].append(karta)
        elif (slovo == "E"):
            slova[4].append(karta)
        brojevi[int(broj) - 1].append(karta)

    slova.sort(key=lambda x: -len(x))
    brojevi.sort(key=lambda x: -len(x))

    if len(slova[0]) == 4 or len(brojevi[0]) == 4:
        return trenutniIgrac
    elif len(spilKarata) == 0:
        if ZbrojiKarte(trenutniIgrac.karte) > ZbrojiKarte(drugiIgrac.karte):
            return trenutniIgrac
        elif ZbrojiKarte(trenutniIgrac.karte) < ZbrojiKarte(drugiIgrac.karte):
            return drugiIgrac
        else:
            return "Izjednaceno"

    else:
        return False


class Server(Agent):
    class PonasanjeServera(FSMBehaviour):
        async def on_start(self):
            print(f"Cekam igrace...\n")

        async def on_end(self):
            await self.agent.stop()


    class CekajIgrace(State):
        async def run(self):
            poruka = await self.receive(timeout=500)
            if poruka:
                sadrzaj = eval(poruka.body)
                if sadrzaj["vrsta"] == "pridruzi_se":
                    igrac = Igrac(sadrzaj["igrac"])
                    igraci.append(igrac)
                    print(f"Igrac se pridruzio... {sadrzaj['igrac']}")
                else:
                    print(f"Nepoznat zahtjev...")
                if len(igraci) == 2:
                    self.set_next_state("pocetak_igre")
                else:
                    self.set_next_state("cekanje_igraca")
            else:
                self.set_next_state("cekanje_igraca")

    class ZapocniIgru(State):
        async def run(self):
            num = random.randint(0, 1)
            global trenutniIgrac
            global drugiIgrac
            trenutniIgrac = igraci[num]
            drugiIgrac = igraci[int(not bool(num))]

            print("Igra pocinje...")
            time.sleep(0.5)
            print("Mijesam spil...")
            time.sleep(0.5)
            print("Dijelim karte...\n")
            time.sleep(0.5)
            random.shuffle(spilKarata)

            for i in range(0, 4):
                igraci[0].karte.append(spilKarata.pop())
                random.shuffle(spilKarata)
                igraci[1].karte.append(spilKarata.pop())

            poruka = Message(
                to=igraci[0].ime,
                body=str(igraci[0].karte),
            )
            await self.send(poruka)

            poruka = Message(
                to=igraci[1].ime,
                body=str(igraci[1].karte),
            )
            await self.send(poruka)

            self.set_next_state("trenutna_igra")

    class Igra(State):
        async def run(self):
            global trenutniIgrac
            global drugiIgrac
            poruka = {
                "vrsta": "tvoj_red",
                "karte": str(trenutniIgrac.karte)
            }
            p = Message(
                to=trenutniIgrac.ime,
                body=str(poruka)
            )
            await self.send(p)

            poruka = await self.receive(timeout=500)
            if len(spilKarata) == 0 or poruka.body is None:
                self.set_next_state("kraj_igre")

            if poruka:
                karta = Karta(poruka.body[0], poruka.body[1])
                trenutniIgrac.karte.remove(karta)

                trenutniIgrac.karte.append(spilKarata.pop())

                rezultatIgre = PronadiPobjednika(trenutniIgrac, drugiIgrac)

                if rezultatIgre == "Izjednaceno":
                    print("Nema pobjednika... Izjednaceno je...\n")
                    porukaTrenutni = "izjednaceno"
                    porukaDrugi = "izjednaceno"
                elif rezultatIgre == trenutniIgrac:
                    print(f"Pobjednik je... {trenutniIgrac.ime}\n")
                    porukaTrenutni = "pobjednik"
                    porukaDrugi = "gubitnik"
                elif rezultatIgre == drugiIgrac:
                    print(f"Pobjednik je... {drugiIgrac.ime}\n")
                    porukaTrenutni = "gubitnik"
                    porukaDrugi = "pobjednik"
                if not rezultatIgre:
                    trenutniIgrac,drugiIgrac = drugiIgrac, trenutniIgrac
                    self.set_next_state("trenutna_igra")
                else:
                    print(f"Karte {trenutniIgrac.ime} su {trenutniIgrac.karte} ")
                    print(f"Karte {drugiIgrac.ime} su {drugiIgrac.karte} ")
                    poruka = {
                        "vrsta": porukaTrenutni,
                        "karte": str(trenutniIgrac.karte)
                    }
                    p = Message(
                        to=trenutniIgrac.ime,
                        body=str(poruka)
                    )
                    await self.send(p)
                    poruka = {
                        "vrsta": porukaDrugi,
                        "karte": str(drugiIgrac.karte)
                    }
                    p = Message(
                        to=drugiIgrac.ime,
                        body=str(poruka)
                    )
                    await self.send(p)
                    self.set_next_state("kraj_igre")

            else:
                self.set_next_state("cekanje_igraca")

    class KrajIgre(State):
        async def run(self):
            print("\nKraj igre, hvala na igranju!")

    async def setup(self):
        stanja = self.PonasanjeServera()

        stanja.add_state(name="cekanje_igraca", state=self.CekajIgrace(), initial=True)
        stanja.add_state(name="pocetak_igre", state=self.ZapocniIgru())
        stanja.add_state(name="trenutna_igra", state=self.Igra())
        stanja.add_state(name="kraj_igre", state=self.KrajIgre())

        stanja.add_transition(source="cekanje_igraca", dest="cekanje_igraca")
        stanja.add_transition(source="cekanje_igraca", dest="pocetak_igre")
        stanja.add_transition(source="pocetak_igre", dest="trenutna_igra")
        stanja.add_transition(source="trenutna_igra", dest="trenutna_igra")
        stanja.add_transition(source="trenutna_igra", dest="kraj_igre")


        self.add_behaviour(stanja)


if __name__ == '__main__':
    server = Server("pogadanje@localhost", "karte123")
    igra = server.start()
    igra.result()

    while server.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break

    server.stop()

    spade.quit_spade()
