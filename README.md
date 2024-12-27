### Start

Executing server:

`docker-compose up --build server_hello`

Executing spade container:

`docker-compose up --build spade_hello`


### Koncepcja

* reprezentujemy strukturę dróg jako graf
* węzły - skrzyżowania
* krawędzie - odcinki dróg pomiędzy skrzyżowaniami
* każda krawędź ma metadane w tym:
    * długość
    * liczba samochodów na tej krawędzi (jak duży jest ruch)
    * jakie jest światło które odpowiada jechaniu w tę stronę (czerwone zwiększa wagę krawędzi)
    * id (pozwala połączyć sygnalizator z krawędzią)
    * coś jeszcze?
* algorytm najkrótszej ścieżki wyznacza trasę pojazdu
* **propozycja uproszczonego modelu**: pozycję pojazdu uprzywilejowanego oznaczamy przez id krawędzi na której się znajduje. Czas przejazdu przez każdą krawędź jest zależny _liniowo_??? od wagi tej krawędzi. Jeżeli samochód 'jedzie' już po krawędzi wymagany czas i światło na kolejnej wybranej krawędzi jest zielone to może na nią wjechać. Jeżeli nie to czeka na zielone.
* Na prezentacji można potem pokazać przykładową trasę w postaci kolejnych snapshotów stanu grafu (pokolorujemy krawędzie w zależności od światła itd.)