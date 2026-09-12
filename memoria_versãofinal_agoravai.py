import os
import sys
import copy
import random
from collections import deque

from escalonadores import RoundRobin, Prioridade, Loteria, CFS
from substituidores import AlgoritmoFIFO, AlgoritmoLRU, AlgoritmoNUF, AlgoritmoOPT


class Process:
    def __init__(self, start, pid, exec_time, priority, tam_memoria_virtual=0,
                 page_sequence=None, chance_es=0):
        self.start = start
        self.pid = pid
        self.exec_time = exec_time
        self.priority = priority
        self.remain_time = exec_time
        self.running_time = 0
        self.waiting_time = 0
        self.blocked_time = 0
        self.start_time = None
        self.finish_time = 0
        self.virtual_runtime = 0
        self.tam_memoria_virtual = tam_memoria_virtual
        self.page_sequence = page_sequence if page_sequence is not None else []
        self.page_index = 0
        self.chance_es = chance_es
        self.estado = "novo"
        self.dispositivo = None
        self.io_restante = 0

    def finished(self):
        return self.remain_time == 0

    def next_page(self):
        if self.page_index >= len(self.page_sequence):
            return None
        page = self.page_sequence[self.page_index]
        self.page_index += 1
        return page


class DispositivoES:
    def __init__(self, identificador, usos_simultaneos, tempo_operacao):
        self.identificador = identificador
        self.usos_simultaneos = usos_simultaneos
        self.tempo_operacao = tempo_operacao
        self.em_uso = []
        self.fila = deque()

    def solicitar(self, processo):
        if len(self.em_uso) < self.usos_simultaneos:
            processo.io_restante = self.tempo_operacao
            self.em_uso.append(processo)
            processo.estado = "bloqueado"
            processo.dispositivo = self.identificador
            return True

        self.fila.append(processo)
        processo.estado = "bloqueado"
        processo.dispositivo = self.identificador
        processo.io_restante = 0
        return False

    def avancar(self):
        concluidos = []

        for processo in list(self.em_uso):
            processo.io_restante -= 1
            if processo.io_restante <= 0:
                self.em_uso.remove(processo)
                processo.estado = "pronto"
                processo.dispositivo = None
                concluidos.append(processo)

        while self.fila and len(self.em_uso) < self.usos_simultaneos:
            processo = self.fila.popleft()
            processo.io_restante = self.tempo_operacao
            self.em_uso.append(processo)

        return concluidos


class GerenciadorES:
    def __init__(self, dispositivos):
        self.dispositivos = {d.identificador: d for d in dispositivos}

    def solicitar(self, processo, identificador):
        self.dispositivos[identificador].solicitar(processo)

    def avancar(self):
        prontos = []
        for dispositivo in self.dispositivos.values():
            prontos.extend(dispositivo.avancar())
        return prontos

    def escolher_dispositivo(self):
        return random.choice(list(self.dispositivos.values()))

    def imprimir(self, processos):
        print("Dispositivos:")
        for dispositivo in self.dispositivos.values():
            usando = [p.pid for p in dispositivo.em_uso]
            esperando = [p.pid for p in dispositivo.fila]
            print(f"Dispositivo {dispositivo.identificador}: usando={usando} esperando={esperando}")

class Memory:
    """
    Representa a memória física como um vetor de frames indexados por número
    de frame. Cada posição armazena (pid, página_virtual) da página carregada,
    ou None se o frame está livre.
    """
    def __init__(self, total_frames):
        self.data = [None] * total_frames

    def alocar(self, frame, pid, pagina_virtual):
        self.data[frame] = (pid, pagina_virtual)

    def desalocar(self, frame):
        self.data[frame] = None

    def conteudo(self, frame):
        return self.data[frame]


ALGORITMOS = {
    'ALTERNANCIA': RoundRobin,
    'PRIORIDADE':  Prioridade,
    'LOTERIA':     Loteria,
    'CFS':         CFS,
}


def calcular_offsets(processos, frame_size):
    """
    Atribui a cada processo um intervalo exclusivo de IDs de página global.
    O ID global de uma página é: offset[pid] + número_da_página.

    O tamanho do intervalo de cada processo é determinado pela maior página
    realmente acessada em sua sequência (não apenas por tam_memoria // frame_size),
    garantindo que processos cujas sequências usem páginas além do limite teórico
    não colidam com o intervalo do processo seguinte.
    """
    offsets = {}
    deslocamento = 0
    for p in processos:
        offsets[p.pid] = deslocamento
        max_pagina = max(p.page_sequence) if p.page_sequence else (p.tam_memoria_virtual // frame_size)
        deslocamento += max_pagina + 1
    return offsets


def construir_sequencia_futura(processos, algoritmo, quantum, frame_size):
    """
    Pré-simula o escalonamento (sem gerenciamento de memória) para obter
    a sequência real de acessos a páginas na ordem em que o escalonador
    as requisita.

    Retorna (sequencia, offsets):
      sequencia : list[int]      — IDs globais de página em ordem de acesso
      offsets   : dict[pid, int] — deslocamento base de cada processo
    """
    offsets = calcular_offsets(processos, frame_size)
    procs = copy.deepcopy(processos)
    pendentes = deque(sorted(procs, key=lambda p: p.start))

    classe = ALGORITMOS[algoritmo.upper()]
    esc = classe(len(procs)) if classe is Loteria else classe()

    sequencia = []
    t = 0

    while True:
        while pendentes and pendentes[0].start <= t:
            esc.chegada(pendentes.popleft())

        if not esc.estrut_dados:
            if not pendentes:
                break
            t = pendentes[0].start
            continue

        processo = esc.selecionar()
        executado = 0
        while executado < quantum and not processo.finished():
            pagina = processo.next_page()
            if pagina is not None:
                sequencia.append(offsets[processo.pid] + pagina)
            processo.remain_time -= 1
            executado += 1

        esc.pos_execucao(processo, executado)
        esc.incrementar_espera(processo, executado)
        t += executado

        if processo.finished():
            processo.finish_time = t
            esc.ao_terminar(processo)
        else:
            esc.apos_quantum(processo)

    return sequencia, offsets


class MemoryManagerState:
    """
    Estado completo de simulação para UM algoritmo de substituição.

    Estruturas
    -------------------
    tabela_processos : dict  pid -> {
        tabela_paginas      : dict[int, int]  — página virtual -> frame físico
        num_frames_alocados : int             — frames em uso por este processo
        limite_frames       : int             — máximo permitido (percentual da VM)
    }
    tabela_frames : dict  frame -> (pid, página_virtual)
        Mapeamento inverso: dado um frame, recupera qual processo/página o ocupa.
    memory : Memory — vetor físico (ilustrativo).

    Política local
        Cada processo recebe fatia exclusiva de frames e instância própria
        de algoritmo com capacidade = limite_frames.
        Chave passada ao algoritmo: número da página virtual (int).

    Política global
        Pool único de frames compartilhado entre todos os processos.
        Instância única de algoritmo com capacidade = total_frames.
        Chave passada ao algoritmo: ID global = offset[pid] + página_virtual,
        garantindo que páginas de processos distintos nunca colidam.
        chave_para_pid_pag mapeia ID global -> (pid, página_virtual) para
        que as substituições possam ser traduzidas de volta ao frame correto.

    Fluxo de acesso (falta de página)
        Processo no limite, política global → substituição local forçada:
            escolher_vitima() restringe a escolha às páginas do próprio processo.
        Demais casos → algoritmo decide livremente dentro de sua capacidade;
            se retornar uma vítima, o frame é reutilizado; caso contrário, um
            frame livre é retirado do pool.
    """

    def __init__(self, politica, total_frames, processos, algoritmo,
                 frame_size, percentual, offsets=None):
        self.politica = politica
        self.tabela_processos = {}
        self.tabela_frames = {}
        self.memory = Memory(total_frames)
        self.offsets = offsets or {}

        for p in processos:
            total_paginas = max(p.tam_memoria_virtual // frame_size, 1)
            limite = max(1, int(total_paginas * percentual / 100))
            self.tabela_processos[p.pid] = {
                "tabela_paginas": {},
                "num_frames_alocados": 0,
                "limite_frames": limite,
            }

        if politica == 'local':
            # Cada processo recebe uma fatia exclusiva de frames
            self.frames_livres_proc = {}
            frame_offset = 0
            for p in processos:
                limite = self.tabela_processos[p.pid]["limite_frames"]
                self.frames_livres_proc[p.pid] = list(range(frame_offset, frame_offset + limite))
                frame_offset += limite
        else:
            self.frames_livres = list(range(total_frames))
            # Mapeamento reverso de ID global para (pid, página) — exclusivo da política global
            self.chave_para_pid_pag = {}

        self.algoritmo = algoritmo

    def obter_algo(self, pid):
        return self.algoritmo[pid] if isinstance(self.algoritmo, dict) else self.algoritmo

    def pegar_frame_livre(self, pid):
        if self.politica == 'local':
            return self.frames_livres_proc[pid].pop(0)
        return self.frames_livres.pop(0)

    def acessar(self, pid, pagina):
        proc = self.tabela_processos.get(pid)
        if proc is None:
            return

        tabela = proc["tabela_paginas"]
        frame = tabela.get(pagina)
        algo = self.obter_algo(pid)

        # ID global único para política global; número de página para local
        chave = (self.offsets[pid] + pagina) if self.politica == 'global' else pagina

        if frame is not None:
            algo.acessar(chave)
            return

        # Falta de página
        no_limite = proc["num_frames_alocados"] >= proc["limite_frames"]

        if self.politica == 'global' and no_limite:
            # Substituição local forçada: vítima restrita às páginas deste processo
            candidatos = {self.offsets[pid] + p for p in tabela}
            chave_vitima = algo.escolher_vitima(candidatos)
            pag_vitima = self.chave_para_pid_pag.pop(chave_vitima)[1]
            e_frame = tabela.pop(pag_vitima)
            proc["num_frames_alocados"] -= 1
            del self.tabela_frames[e_frame]
            self.memory.desalocar(e_frame)
            algo.forcar_troca(chave_vitima, chave)
            algo.avancar()  # mantém o índice do OPT alinhado à sequência de acessos
            frame = e_frame
        else:
            chave_removida = algo.acessar(chave)

            if chave_removida is not None:
                if self.politica == 'local':
                    e_pid, pag_vitima = pid, chave_removida
                else:
                    e_pid, pag_vitima = self.chave_para_pid_pag.pop(chave_removida)

                e_frame = self.tabela_processos[e_pid]["tabela_paginas"].pop(pag_vitima)
                self.tabela_processos[e_pid]["num_frames_alocados"] -= 1
                del self.tabela_frames[e_frame]
                self.memory.desalocar(e_frame)
                frame = e_frame
            else:
                frame = self.pegar_frame_livre(pid)

        tabela[pagina] = frame
        proc["num_frames_alocados"] += 1
        self.tabela_frames[frame] = (pid, pagina)
        self.memory.alocar(frame, pid, pagina)
        if self.politica == 'global':
            self.chave_para_pid_pag[chave] = (pid, pagina)

    def obter_trocas(self):
        if isinstance(self.algoritmo, dict):
            return sum(a.swaps for a in self.algoritmo.values())
        return self.algoritmo.swaps


class MemoryManager:
    """
    Executa os 4 algoritmos de substituição em paralelo, cada um com seu
    próprio MemoryManagerState (tabelas e pool de frames independentes).

    Política local  → instância de algoritmo por processo; chaves são
                      números de página virtual.
    Política global → instância única por algoritmo; chaves são IDs globais
                      (offset[pid] + página) para evitar colisão entre processos.
                      A sequência futura do OPT é construída pré-simulando o
                      escalonamento, refletindo a ordem real de execução.
    """
    def __init__(self, politica, tam_memoria, frame_size, percentual,
                 processos, algoritmo=None, quantum=None):
        self.politica = politica
        self.frame_size = frame_size
        self.percentual = percentual
        self.total_frames = tam_memoria // frame_size

        def frames_processo(p):
            paginas = max(p.tam_memoria_virtual // frame_size, 1)
            return max(1, int(paginas * percentual / 100))

        if politica == 'local':
            algos = {
                'fifo': {p.pid: AlgoritmoFIFO(frames_processo(p)) for p in processos},
                'lru':  {p.pid: AlgoritmoLRU(frames_processo(p)) for p in processos},
                'nuf':  {p.pid: AlgoritmoNUF(frames_processo(p)) for p in processos},
                'opt':  {p.pid: AlgoritmoOPT(frames_processo(p), p.page_sequence)
                         for p in processos},
            }
            common = dict(politica=politica, total_frames=self.total_frames,
                          processos=processos, frame_size=frame_size, percentual=percentual)
        else:
            # Pré-simula o escalonamento para obter a ordem real de acessos
            sequencia, offsets = construir_sequencia_futura(
                processos, algoritmo, quantum, frame_size)
            algos = {
                'fifo': AlgoritmoFIFO(self.total_frames),
                'lru':  AlgoritmoLRU(self.total_frames),
                'nuf':  AlgoritmoNUF(self.total_frames),
                'opt':  AlgoritmoOPT(self.total_frames, sequencia),
            }
            common = dict(politica=politica, total_frames=self.total_frames,
                          processos=processos, frame_size=frame_size,
                          percentual=percentual, offsets=offsets)

        self.sims = {name: MemoryManagerState(**common, algoritmo=algo)
                      for name, algo in algos.items()}

    def acessar(self, pid, pagina):
        """Roteia o acesso aos 4 estados de simulação em paralelo."""
        if pagina is None:
            return
        for sim in self.sims.values():
            sim.acessar(pid, pagina)

    def obter_trocas(self):
        """Retorna (trocas_fifo, trocas_lru, trocas_nuf, trocas_opt)."""
        return tuple(self.sims[k].obter_trocas() for k in ('fifo', 'lru', 'nuf', 'opt'))


class CPU:
    def __init__(self, quantum, algoritmo, processos, mem_manager, gerenciador_es):
        self.quantum = quantum
        self.processos = processos
        self.pendentes = deque(sorted(processos, key=lambda p: p.start))
        self.escalonador = self.get_escalonador(algoritmo)
        self.time = 0
        self.log = []
        self.mem_manager = mem_manager
        self.gerenciador_es = gerenciador_es

    def get_escalonador(self, codigo):
        if codigo.upper() not in ALGORITMOS:
            print(f"Algoritmo inválido. Opções válidas: {', '.join(ALGORITMOS.keys())}")
            sys.exit(1)
        classe = ALGORITMOS[codigo.upper()]
        return classe(len(self.processos)) if classe is Loteria else classe()

    def admitir_novo_processo(self):
        while self.pendentes and self.pendentes[0].start <= self.time:
            processo = self.pendentes.popleft()
            processo.estado = "pronto"
            self.escalonador.chegada(processo)

    def atualizar_bloqueados(self):
        for processo in self.processos:
            if processo.estado == "bloqueado":
                processo.blocked_time += 1

        prontos = self.gerenciador_es.avancar()
        for processo in prontos:
            self.escalonador.chegada(processo)

    def imprimir_estado(self, atual=None):
        if atual is not None:
            print(f"CPU: P{atual.pid} restante={atual.remain_time}")

        prontos = [p for p in self.processos if p.estado == "pronto"]
        bloqueados = [p for p in self.processos if p.estado == "bloqueado"]

        print("Prontos:", [(p.pid, p.remain_time) for p in prontos])
        print("Bloqueados:",
              [(p.pid, p.remain_time, p.dispositivo) for p in bloqueados])
        self.gerenciador_es.imprimir(self.processos)

    def executar_processo(self, processo):
        if processo.start_time is None:
            processo.start_time = self.time

        processo.estado = "executando"
        executado = 0

        vai_fazer_es = (
            bool(self.gerenciador_es.dispositivos)
            and random.randint(1, 100) <= processo.chance_es
        )

        momento_es = random.randint(1, self.quantum) if vai_fazer_es else None
        dispositivo = self.gerenciador_es.escolher_dispositivo() if vai_fazer_es else None

        while executado < self.quantum and not processo.finished():
            pagina = processo.next_page()
            self.mem_manager.acessar(processo.pid, pagina)

            processo.remain_time -= 1
            processo.running_time += 1
            executado += 1

            self.escalonador.incrementar_espera(processo, 1)
            self.atualizar_bloqueados()
            self.time += 1

            self.admitir_novo_processo()

            if processo.finished():
                processo.estado = "terminado"
                processo.finish_time = self.time
                return executado

            if momento_es is not None and executado == momento_es:
                self.gerenciador_es.solicitar(processo, dispositivo.identificador)
                self.imprimir_estado()
                return executado

        processo.estado = "pronto"
        return executado

    def avancar_tempo_sem_cpu(self):
        self.atualizar_bloqueados()
        self.time += 1
        self.admitir_novo_processo()

    def run(self):
        esc = self.escalonador

        while True:
            self.admitir_novo_processo()

            if not esc.estrut_dados:
                if not self.pendentes and not any(
                    p.estado == "bloqueado" for p in self.processos
                ):
                    break

                self.avancar_tempo_sem_cpu()
                continue

            processo = esc.selecionar()
            processo.estado = "executando"
            self.imprimir_estado(processo)

            executado = self.executar_processo(processo)

            if processo.finished():
                esc.ao_terminar(processo)
            elif processo.estado == "bloqueado":
                esc.retirar(processo)
            else:
                esc.pos_execucao(processo, executado)
                esc.apos_quantum(processo)

        for processo in self.processos:
            tempo_total = processo.finish_time - processo.start
            print(
                f"P{processo.pid}: total={tempo_total} "
                f"pronto={processo.waiting_time} "
                f"bloqueado={processo.blocked_time}"
            )

def ler_arquivo(nome_arquivo):
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome_arquivo)
    with open(caminho, "r") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    config = linhas[0].split("|")
    algoritmo = config[0].strip().upper()
    fatia = int(config[1].strip())
    politica_memoria = config[2].strip().lower()
    tamanho_memoria = int(config[3])
    tamanho_pagina = int(config[4])
    percentual_alocacao = int(config[5])
    num_dispositivos = int(config[6])

    dispositivos = []
    indice = 1

    for _ in range(num_dispositivos):
        partes = linhas[indice].split("|")
        dispositivos.append(
            DispositivoES(
                partes[0].strip(),
                int(partes[1]),
                int(partes[2])
            )
        )
        indice += 1

    processos = []
    for linha in linhas[indice:]:
        partes = linha.split("|")
        start = int(partes[0])
        pid = int(partes[1])
        exec_time = int(partes[2])
        priority = int(partes[3])
        tam_memoria = int(partes[4])
        page_sequence = list(map(int, partes[5].split())) if partes[5].strip() else []
        chance_es = int(partes[6])

        processos.append(
            Process(
                start, pid, exec_time, priority,
                tam_memoria, page_sequence, chance_es
            )
        )

    return (
        algoritmo, fatia, politica_memoria, tamanho_memoria,
        tamanho_pagina, percentual_alocacao, dispositivos, processos
    )


def clonar(processos):
    return [copy.deepcopy(p) for p in processos]


def imprimir_resultado_memoria(fifo, lru, nuf, opt):
    diffs = {'FIFO': abs(fifo - opt), 'LRU': abs(lru - opt), 'NUF': abs(nuf - opt)}
    minimo = min(diffs.values())
    melhores = [nome for nome, d in diffs.items() if d == minimo]
    melhor = 'empate' if len(melhores) > 1 else melhores[0]
    print(f"{fifo}|{lru}|{nuf}|{opt}|{melhor}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python memoria_versãofinal_agoravai.py <arquivo_entrada>")
        sys.exit(1)

    (algoritmo, fatia, politica_memoria, tamanho_memoria,
     tamanho_pagina, percentual_alocacao, dispositivos,
     processos_base) = ler_arquivo(sys.argv[1])

    processos = clonar(processos_base)

    mem = MemoryManager(
        politica_memoria,
        tamanho_memoria,
        tamanho_pagina,
        percentual_alocacao,
        processos,
        algoritmo=algoritmo,
        quantum=fatia
    )

    gerenciador_es = GerenciadorES(dispositivos)
    cpu = CPU(fatia, algoritmo, processos, mem, gerenciador_es)
    cpu.run()

    fifo, lru, nuf, opt = mem.obter_trocas()
    imprimir_resultado_memoria(fifo, lru, nuf, opt)


if __name__ == "__main__":
    main()