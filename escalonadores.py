import random
import heapq
from abc import ABC, abstractmethod


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
        guarda os processos de um jeito diferente, então cada classe
        implementa a sua própria forma de remover.
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
    chamado "prioridade (ou bilhetes)"). Para sortear quem usa a CPU,
    soma-se todos os bilhetes, sorteia-se um número entre 1 e essa soma,
    e percorre-se a lista de processos somando os bilhetes de cada um até
    ultrapassar o número sorteado. O dono do bilhete sorteado é o
    escolhido. É o mesmo princípio de uma rifa comum.
    """
    def __init__(self):
        super().__init__("Loteria", list())

    def __iter__(self):
        return iter(self.estrut_dados)

    def selecionar(self):
        total_bilhetes = sum(p.priority for p in self.estrut_dados)
        if total_bilhetes <= 0:
            return random.choice(self.estrut_dados)

        sorteio = random.randint(1, total_bilhetes)
        soma = 0
        for p in self.estrut_dados:
            soma += p.priority
            if sorteio <= soma:
                return p
        return self.estrut_dados[-1]

    def chegada(self, processo):
        self.estrut_dados.append(processo)

    def ao_terminar(self, processo):
        self.estrut_dados.remove(processo)

    def retirar(self, processo):
        if processo in self.estrut_dados:
            self.estrut_dados.remove(processo)


class CFS(Escalonador):
    """
    Versão simplificada do CFS (Completely Fair Scheduler) do Linux.
    Cada processo tem um virtual_runtime, que cresce conforme ele usa a
    CPU (o quanto cresce depende da prioridade, que aqui funciona como
    peso). O escalonador sempre escolhe o processo com o menor
    virtual_runtime, guardado em uma fila de prioridade (heap). Assim,
    quem usou menos CPU até agora tem preferência na próxima escolha.

    Diferente da classe Prioridade, aqui selecionar() já remove o
    processo do heap (heappop). Por isso ao_terminar não precisa fazer
    nada, e retirar só encontra algo para remover se o processo ainda
    não tiver chegado a ser escolhido.
    """
    def __init__(self):
        super().__init__("CFS (Completely Fair Scheduler)", list())
        self._ordem = 0

    def __iter__(self):
        return (item[2] for item in self.estrut_dados)

    def selecionar(self):
        return heapq.heappop(self.estrut_dados)[2]

    def chegada(self, processo):
        heapq.heappush(self.estrut_dados, (processo.virtual_runtime, self._ordem, processo))
        self._ordem += 1

    def ao_terminar(self, processo):
        pass

    def pos_execucao(self, processo, n):
        processo.virtual_runtime += n * processo.priority

    def apos_quantum(self, processo):
        heapq.heappush(self.estrut_dados, (processo.virtual_runtime, self._ordem, processo))
        self._ordem += 1

    def retirar(self, processo):
        for item in self.estrut_dados:
            if item[2] is processo:
                self.estrut_dados.remove(item)
                heapq.heapify(self.estrut_dados)
                break