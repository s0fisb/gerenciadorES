import random
import heapq
from abc import ABC, abstractmethod
from bintrees import RBTree


# Estrutura para a fila de loteria. Uma arvore de Fenwick (Binary Indexed
# Tree) guarda a soma de bilhetes das posicoes do vetor de processos,
# permitindo sortear um processo em tempo O(log n) em vez de percorrer a
# lista inteira somando bilhetes a cada sorteio.
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
    """
    Guarda os processos da loteria em um vetor de posicoes fixas, de
    tamanho igual ao numero total de processos do sistema. A arvore de
    Fenwick por cima do vetor guarda a soma de bilhetes, para sortear
    rapido quem vai usar a CPU.

    Quando um processo sai da fila (por E/S ou por terminar), a posicao
    dele no vetor fica livre e volta para uma pilha de posicoes livres
    (self._livres), para ser reaproveitada da proxima vez que algum
    processo entrar. Sem isso, cada entrada nova (inclusive quando um
    processo volta de uma operacao de E/S) ocuparia uma posicao nova,
    e o vetor acabaria estourando o espaco.
    """
    def __init__(self, n):
        self._ft = FenwickTree(n)
        self._slots = [None] * n
        self._pid_slot = {}
        self._livres = list(range(n - 1, -1, -1))

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

    @abstractmethod
    def retirar(self, processo):
        """
        Remove o processo da estrutura do escalonador quando ele é
        bloqueado para realizar uma operação de E/S. Cada algoritmo
        guarda os processos de um jeito diferente (lista, heap, arvore
        rubro-negra, fila de loteria), então cada classe implementa a
        sua própria forma de remover.
        """
        pass

    def apos_quantum(self, processo):
        pass

    def pos_execucao(self, processo, executado):
        pass

    def incrementar_espera(self, processo_atual, n):
        for p in self:
            if p is not processo_atual:
                p.waiting_time += n


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

    def retirar(self, processo):
        if processo in self.estrut_dados:
            self.estrut_dados.remove(processo)
            if self.estrut_dados:
                self._idx %= len(self.estrut_dados)
            else:
                self._idx = 0


class Prioridade(Escalonador):
    """
    Escalonador por prioridade, usando uma fila de prioridade (heap).
    Cada item guardado é uma tupla (prioridade, ordem_chegada, processo).
    O campo ordem_chegada só serve para desempatar prioridades iguais,
    assim o heap nunca precisa comparar dois objetos Process entre si.

    Importante: selecionar() apenas olha o topo do heap, não remove.
    Isso é necessário porque, enquanto o processo do topo está rodando,
    outros processos podem chegar e entrar no heap (admitir_novo_processo).
    Por isso, tanto ao_terminar quanto retirar procuram o processo certo
    pela identidade dele, em vez de simplesmente tirar o que está no topo
    no momento, que pode já não ser mais o mesmo processo que rodou.
    """
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
        self.retirar(processo)

    def retirar(self, processo):
        for item in self.estrut_dados:
            if item[2] is processo:
                self.estrut_dados.remove(item)
                heapq.heapify(self.estrut_dados)
                break


class Loteria(Escalonador):
    """
    Escalonador por loteria. Cada processo pronto recebe uma quantidade
    de bilhetes igual à sua prioridade (o campo do arquivo de entrada
    chamado "prioridade (ou bilhetes)"). O sorteio em si é feito pela
    LotteryQueue, definida no topo deste arquivo, usando uma árvore de
    Fenwick para ser rápido mesmo com muitos processos.
    """
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

    def retirar(self, processo):
        self.estrut_dados.remove(processo)


class CFS(Escalonador):
    """
    Versão simplificada do CFS (Completely Fair Scheduler) do Linux.
    Cada processo tem um virtual_runtime, que cresce conforme ele usa a
    CPU (o quanto cresce depende da prioridade, que aqui funciona como
    peso). O escalonador guarda os processos em uma árvore rubro-negra
    (RBTree, da biblioteca bintrees), ordenada pela chave
    (virtual_runtime, prioridade, pid). Como a árvore fica sempre
    ordenada, o processo com menor virtual_runtime está sempre na
    primeira posição, e é ele quem deve ser escolhido para rodar.

    Diferente da classe Prioridade, aqui selecionar() já remove o
    processo da árvore (pop). Por isso ao_terminar não precisa fazer
    nada, e retirar só encontra algo para remover se o processo ainda
    não tiver chegado a ser escolhido.
    """
    def __init__(self):
        super().__init__("CFS (Completely Fair Scheduler)", RBTree())

    def __iter__(self):
        return self.estrut_dados.values()

    def selecionar(self):
        return self.estrut_dados.pop(next(iter(self.estrut_dados)))

    def chegada(self, processo):
        chave = (processo.virtual_runtime, processo.priority, processo.pid)
        self.estrut_dados[chave] = processo

    def ao_terminar(self, processo):
        pass

    def pos_execucao(self, processo, n):
        processo.virtual_runtime += n * processo.priority

    def apos_quantum(self, processo):
        chave = (processo.virtual_runtime, processo.priority, processo.pid)
        self.estrut_dados[chave] = processo

    def retirar(self, processo):
        chave = (processo.virtual_runtime, processo.priority, processo.pid)
        if chave in self.estrut_dados:
            self.estrut_dados.pop(chave)