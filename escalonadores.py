import random
from abc import ABC, abstractmethod
import heapq
from bintrees import RBTree

## ESTRUTURA PARA FILA DE LOTERIA, GERADO POR IA
class FenwickTree:
    def __init__(self, n):
        self._n = n
        self._tree = [0] * (n + 1)

    def update(self, i, delta):
        i += 1
        while i <= self._n:
            self._tree[i] += delta
            i += i & (-i)

    def prefix(self, i):
        i += 1
        s = 0
        while i > 0:
            s += self._tree[i]
            i -= i & (-i)
        return s

    def total(self):
        return self.prefix(self._n - 1)

    def find_kth(self, k):
        pos = 0
        for b in range(self._n.bit_length(), -1, -1):
            nxt = pos + (1 << b)
            if nxt <= self._n and self._tree[nxt] < k:
                pos = nxt
                k -= self._tree[pos]
        return pos


class LotteryQueue:
    def __init__(self, n):
        self._ft = FenwickTree(n)
        self._slots = [None] * n
        self._pid_slot = {}
        self._livres = list(range(n))

    def add(self, p):
        slot = self._livres.pop()
        self._slots[slot] = p
        self._pid_slot[p.pid] = slot
        self._ft.update(slot, p.priority)

    def draw(self):
        k = random.randint(1, self._ft.total())
        return self._slots[self._ft.find_kth(k)]

    def remove(self, p):
        slot = self._pid_slot.pop(p.pid)
        self._slots[slot] = None
        self._ft.update(slot, -p.priority)
        self._livres.append(slot)

    def __iter__(self):
        return (p for p in self._slots if p is not None)

    def __bool__(self):
        return self._ft.total() > 0
###


# Estrutura de dados para escalonadores, feito como classe abstrata.
# Aplicando conteudo visto em Linguagens de Programação =D
class Escalonador(ABC):
    def __init__(self, nome, estrut_dados):
        self.nome = nome
        self.estrut_dados = estrut_dados
    
    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def selecionar(self):
        pass

    @abstractmethod
    def chegada(self, processo):
        pass

    @abstractmethod
    def ao_terminar(self, processo):
        pass

    def apos_quantum(self, processo):
        pass

    def pos_execucao(self, processo, executado):
        pass

    def incrementar_espera(self, processo_atual, n):
        for p in self:
            if p is not processo_atual:
                p.waiting_time += n

    def retirar(self, processo):
        if isinstance(self.estrut_dados, list):
            if processo in self.estrut_dados:
                self.estrut_dados.remove(processo)
                if hasattr(self, '_idx') and self.estrut_dados:
                    self._idx %= len(self.estrut_dados)
        elif isinstance(self.estrut_dados, LotteryQueue):
            self.estrut_dados.remove(processo)
        elif isinstance(self.estrut_dados, RBTree):
            chave = (processo.virtual_runtime, processo.priority, processo.pid)
            if chave in self.estrut_dados:
                self.estrut_dados.pop(chave)
        else:
            for item in list(self.estrut_dados):
                if len(item) == 3 and item[2] is processo:
                    self.estrut_dados.remove(item)
                    heapq.heapify(self.estrut_dados)
                    break

class RoundRobin(Escalonador):
    def __init__(self):
        super().__init__("Round-Robin (Alternância Circular)", list())
        self._idx = 0

    def __iter__(self):
        return iter(self.estrut_dados)

    def selecionar(self):
        if self._idx >= len(self.estrut_dados):
            self._idx = 0
        return self.estrut_dados[self._idx]

    def chegada(self, processo):
        self.estrut_dados.append(processo)

    def ao_terminar(self, processo):
        idx = self.estrut_dados.index(processo)
        self.estrut_dados.pop(idx)
        if self.estrut_dados and self._idx >= len(self.estrut_dados):
            self._idx = 0

    def apos_quantum(self, processo):
        if self.estrut_dados:
            self._idx = (self._idx + 1) % len(self.estrut_dados)

class Prioridade(Escalonador):
    def __init__(self):
        super().__init__("Prioridade", list())
        self._ordem = 0

    def __iter__(self):
        return (item[2] for item in self.estrut_dados)

    def selecionar(self):
        return self.estrut_dados[0][2]

    def chegada(self, processo):
        heapq.heappush(self.estrut_dados, (processo.priority, self._ordem, processo))
        self._ordem += 1

    def ao_terminar(self, processo):
        heapq.heappop(self.estrut_dados)


class Loteria(Escalonador):
    def __init__(self, n):
        super().__init__("Loteria", LotteryQueue(n))

    def __iter__(self):
        return iter(self.estrut_dados)

    def selecionar(self):
        return self.estrut_dados.draw()

    def chegada(self, processo):
        self.estrut_dados.add(processo)

    def ao_terminar(self, processo):
        self.estrut_dados.remove(processo)

class CFS(Escalonador):
    def __init__(self):
        super().__init__("CFS (Completely Fair Scheduler)", RBTree())

    def __iter__(self):
        return self.estrut_dados.values()

    def selecionar(self):
        return self.estrut_dados.pop(next(iter(self.estrut_dados)))

    def chegada(self, processo):
        self.estrut_dados[(processo.virtual_runtime, processo.priority, processo.pid)] = processo

    def ao_terminar(self, processo):
        pass

    def pos_execucao(self, processo, n):
        processo.virtual_runtime += n * processo.priority

    def apos_quantum(self, processo):
        self.estrut_dados[(processo.virtual_runtime, processo.priority, processo.pid)] = processo
