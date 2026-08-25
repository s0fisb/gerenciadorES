from collections import OrderedDict, deque

"""
Interface comum dos algoritmos
-------------------------------
Cada classe recebe `num_frames` (capacidade máxima) e expõe:

  acessar(chave) -> chave_removida | None
      Registra um acesso à página `chave`.
      - Hit  : atualiza o estado interno e retorna None.
      - Falta sem espaço: escolhe a vítima, remove-a internamente,
        incrementa `swaps` e retorna a vítima.
      - Falta com espaço: insere a chave e retorna None.

  escolher_vitima(candidatos) -> chave
      Retorna qual chave do conjunto `candidatos` seria escolhida como
      vítima pelo algoritmo, sem alterar o estado interno.

  forcar_troca(vitima, nova_chave)
      Remove `vitima`, insere `nova_chave` e incrementa `swaps`.

  avancar()
      Registra que um acesso à memória ocorreu sem passar por `acessar`
      (caso da substituição local forçada na política global). Só o OPT
      usa essa informação, para manter o índice da sequência futura
      alinhado com a ordem real dos acessos.

  swaps : int  — total de substituições (trocas) realizadas.

Para política local, `chave` é o número de página virtual (int).
Para política global, `chave` é o ID global da página (int).
"""


class AlgoritmoFIFO:
    """
    Estrutura: deque (ordem de chegada) + set (teste de presença O(1)).
    Vítima: página que está há mais tempo na memória (cabeça da fila).
    """
    def __init__(self, num_frames, future=None):
        self.num_frames = num_frames
        self.fila = deque()    # ordem de carga
        self.conjunto = set()  # páginas atualmente na memória
        self.swaps = 0

    def acessar(self, chave):
        if chave in self.conjunto:
            return None
        removida = None
        if len(self.conjunto) >= self.num_frames:
            removida = self.fila.popleft()
            self.conjunto.discard(removida)
            self.swaps += 1
        self.conjunto.add(chave)
        self.fila.append(chave)
        return removida

    def escolher_vitima(self, candidatos):
        """Retorna a vítima FIFO dentro de candidatos: a que chegou primeiro."""
        for chave in self.fila:
            if chave in candidatos:
                return chave
        return next(iter(candidatos))

    def forcar_troca(self, vitima, nova_chave):
        self.conjunto.discard(vitima)
        self.fila = deque(c for c in self.fila if c != vitima)
        self.conjunto.add(nova_chave)
        self.fila.append(nova_chave)
        self.swaps += 1

    def avancar(self):
        pass


class AlgoritmoLRU:
    """
    Estrutura: OrderedDict — mantém as páginas em ordem de acesso mais recente.
    Vítima: página menos recentemente usada (primeira do OrderedDict).
    No hit, move_to_end atualiza a recência.
    """
    def __init__(self, num_frames, future=None):
        self.num_frames = num_frames
        self.ordem = OrderedDict()  # chave -> True, ordenado por acesso
        self.swaps = 0

    def acessar(self, chave):
        if chave in self.ordem:
            self.ordem.move_to_end(chave)
            return None
        removida = None
        if len(self.ordem) >= self.num_frames:
            removida, _ = self.ordem.popitem(last=False)
            self.swaps += 1
        self.ordem[chave] = True
        return removida

    def escolher_vitima(self, candidatos):
        """Retorna a vítima LRU dentro de candidatos: a menos recentemente usada."""
        for chave in self.ordem:
            if chave in candidatos:
                return chave
        return next(iter(candidatos))

    def forcar_troca(self, vitima, nova_chave):
        if vitima in self.ordem:
            del self.ordem[vitima]
        self.ordem[nova_chave] = True
        self.swaps += 1

    def avancar(self):
        pass


class AlgoritmoNUF:
    """
    Estrutura: set de páginas em memória + dict de contadores de acesso.
    Vítima: página com menor contador; empates resolvidos pelo valor da chave.
    No hit o contador é incrementado.
    """
    def __init__(self, num_frames, future=None):
        self.num_frames = num_frames
        self.conjunto = set()
        self.contadores = {}  # chave -> número de acessos
        self.swaps = 0

    def acessar(self, chave):
        if chave in self.conjunto:
            self.contadores[chave] = self.contadores.get(chave, 0) + 1
            return None
        removida = None
        if len(self.conjunto) >= self.num_frames:
            removida = min(self.conjunto,
                           key=lambda k: (self.contadores.get(k, 0), k))
            self.conjunto.discard(removida)
            self.contadores.pop(removida, None)
            self.swaps += 1
        self.conjunto.add(chave)
        self.contadores[chave] = 1
        return removida

    def escolher_vitima(self, candidatos):
        """Retorna a vítima NUF dentro de candidatos: a com menor frequência de acesso."""
        return min(candidatos, key=lambda k: (self.contadores.get(k, 0), k))

    def forcar_troca(self, vitima, nova_chave):
        self.conjunto.discard(vitima)
        self.contadores.pop(vitima, None)
        self.conjunto.add(nova_chave)
        self.contadores[nova_chave] = 1
        self.swaps += 1

    def avancar(self):
        pass


class AlgoritmoOPT:
    """
    Estrutura: set de páginas em memória + lista `futuro` com a sequência
               completa de acessos futuros passada no construtor.
    Vítima: página cujo próximo uso está mais distante no futuro (inf se nunca).
    `indice` rastreia a posição corrente na sequência futura.

    Para política global, `futuro` contém os IDs globais das páginas na ordem
    real de execução obtida pré-simulando o escalonamento.
    """
    def __init__(self, num_frames, future):
        self.num_frames = num_frames
        self.conjunto = set()
        self.futuro = list(future) if future else []
        self.indice = 0
        self.swaps = 0

    def acessar(self, chave):
        idx = self.indice
        self.indice += 1
        if chave in self.conjunto:
            return None
        removida = None
        if len(self.conjunto) >= self.num_frames:
            removida = self.proxima_vitima(self.conjunto, idx)
            self.conjunto.discard(removida)
            self.swaps += 1
        self.conjunto.add(chave)
        return removida

    def proxima_vitima(self, pool, idx):
        def proximo_uso(k):
            for i in range(idx + 1, len(self.futuro)):
                if self.futuro[i] == k:
                    return i
            return float('inf')
        return max(pool, key=proximo_uso)

    def escolher_vitima(self, candidatos):
        """Retorna a vítima OPT dentro de candidatos: a com uso mais distante no futuro."""
        return self.proxima_vitima(candidatos, self.indice)

    def forcar_troca(self, vitima, nova_chave):
        self.conjunto.discard(vitima)
        self.conjunto.add(nova_chave)
        self.swaps += 1

    def avancar(self):
        # Consome a posição corrente da sequência futura sem registrar acesso
        # (a substituição local forçada não passa por `acessar`).
        self.indice += 1


FIFO = AlgoritmoFIFO
LRU  = AlgoritmoLRU
NUF  = AlgoritmoNUF
OPT  = AlgoritmoOPT
