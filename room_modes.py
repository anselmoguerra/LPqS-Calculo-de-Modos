#!/usr/bin/env python3
"""Room modal calculator based on the MODOS2026 spreadsheet logic.

The core modal frequency equation for a rectangular room is:

    f = c / 2 * sqrt((p / L)^2 + (q / W)^2 + (r / H)^2)

where:
    c = 20.06 * sqrt(temperature_c + 273)
    L, W, H are room length, width, and height in meters
    p, q, r are non-negative integer mode indices, not all zero

Mode classification:
    axial:      exactly one index is non-zero
    tangential: exactly two indices are non-zero
    oblique:    all three indices are non-zero
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

os.environ.setdefault(
    "MPLCONFIGDIR",
    "/private/tmp/acustica-salas-codex-matplotlib",
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DEFAULT_BANDS = (25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250)
EXAMPLE_ROOMS = {
    "small": (3.0, 3.6, 2.4),
    "studio": (5.2, 7.1, 3.1),
    "concert": (18.0, 28.0, 11.0),
}
MODE_COLORS = {
    "axial": "#b84a4a",
    "tangential": "#4f84b8",
    "oblique": "#5f9e6e",
}
MODAL_DENSITY_WEIGHTS = {
    "axial": 1.0,
    "tangential": 0.5,
    "oblique": 0.25,
}


@dataclass(frozen=True)
class Room:
    length: float
    width: float
    height: float
    temperature_c: float = 24.0

    @property
    def speed_of_sound(self) -> float:
        return 20.06 * math.sqrt(self.temperature_c + 273.0)

    @property
    def volume(self) -> float:
        return self.length * self.width * self.height

    @property
    def surface_area(self) -> float:
        return 2.0 * (
            self.length * self.width
            + self.length * self.height
            + self.width * self.height
        )

    @property
    def spreadsheet_schroeder_label(self) -> float:
        return 3.0 * self.speed_of_sound / min(self.length, self.width, self.height)


@dataclass(frozen=True)
class Mode:
    p: int
    q: int
    r: int
    frequency_hz: float
    rounded_hz: int
    classification: str


@dataclass(frozen=True)
class RatioWarning:
    severity: str
    message: str


@dataclass(frozen=True)
class AcousticRecommendation:
    frequency: str
    mode_type: str
    severity: str
    likely_audible_effect: str
    suggested_treatment: str
    caution: str


def classify_mode(p: int, q: int, r: int) -> str:
    non_zero = sum(index > 0 for index in (p, q, r))
    if non_zero == 1:
        return "axial"
    if non_zero == 2:
        return "tangential"
    if non_zero == 3:
        return "oblique"
    raise ValueError("mode indices cannot all be zero")


def modal_frequency(room: Room, p: int, q: int, r: int) -> float:
    return room.speed_of_sound / 2.0 * math.sqrt(
        (p / room.length) ** 2
        + (q / room.width) ** 2
        + (r / room.height) ** 2
    )


def room_ratio(room: Room) -> tuple[float, float, float]:
    shortest, middle, longest = sorted((room.length, room.width, room.height))
    return 1.0, middle / shortest, longest / shortest


def ratio_warnings(room: Room, modes: list[Mode]) -> list[RatioWarning]:
    warnings: list[RatioWarning] = []
    dimensions = {
        "comprimento": room.length,
        "largura": room.width,
        "altura": room.height,
    }
    items = list(dimensions.items())

    for i, (name_a, value_a) in enumerate(items):
        for name_b, value_b in items[i + 1 :]:
            ratio = max(value_a, value_b) / min(value_a, value_b)
            if abs(ratio - 1.0) <= 0.05:
                warnings.append(
                    RatioWarning(
                        "alto",
                        f"{name_a} e {name_b} sao quase iguais. Salas quase cubicas concentram modos nas mesmas frequencias.",
                    )
                )
            for integer_ratio in (2, 3):
                if abs(ratio - integer_ratio) / integer_ratio <= 0.03:
                    warnings.append(
                        RatioWarning(
                            "alto",
                            f"{name_a} e {name_b} estao perto de uma proporcao {integer_ratio}:1. Isso pode reforcar cancelamentos e ressonancias.",
                        )
                    )

    axial_modes = [mode for mode in modes if mode.classification == "axial"]
    axial_by_frequency = Counter(mode.rounded_hz for mode in axial_modes)
    coincident = [frequency for frequency, count in axial_by_frequency.items() if count > 1]
    if coincident:
        joined = ", ".join(str(frequency) for frequency in coincident[:8])
        warnings.append(
            RatioWarning(
                "alto",
                f"Ha modos axiais coincidentes ou quase coincidentes em {joined} Hz. Coincidencias axiais costumam soar como graves 'sobrando'.",
            )
        )

    first_axials = sorted(mode.frequency_hz for mode in axial_modes)[:6]
    for lower, upper in zip(first_axials, first_axials[1:]):
        if upper - lower < 5.0:
            warnings.append(
                RatioWarning(
                    "medio",
                    f"Dois dos primeiros modos axiais estao separados por apenas {upper - lower:.1f} Hz ({lower:.1f} e {upper:.1f} Hz).",
                )
            )
            break

    _, middle_ratio, longest_ratio = room_ratio(room)
    if middle_ratio < 1.10 or longest_ratio < 1.40:
        warnings.append(
            RatioWarning(
                "medio",
                f"A proporcao normalizada 1:{middle_ratio:.2f}:{longest_ratio:.2f} e pouco espalhada. Dimensoes mais diferentes distribuem melhor os modos.",
            )
        )

    if not warnings:
        warnings.append(
            RatioWarning(
                "ok",
                "Nenhum problema simples de proporcao foi detectado. Ainda assim, a decisao acustica final depende de materiais, posicao de fontes e ouvintes.",
            )
        )

    return warnings


def frequency_region(frequency_hz: float) -> str:
    if frequency_hz < 80:
        return "frequencia muito baixa; prioridade para graves"
    if frequency_hz < 250:
        return "regiao modal grave/medio-grave"
    if frequency_hz < 700:
        return "regiao de transicao"
    return "menos dominada por modos; controlar reflexoes e difusao"


def frequency_region_index(frequency_hz: float) -> int:
    if frequency_hz < 80:
        return 0
    if frequency_hz < 250:
        return 1
    if frequency_hz < 700:
        return 2
    return 3


def treatment_for_frequency(frequency_hz: float, issue: str) -> str:
    if frequency_hz < 80:
        return "armadilhas de grave espessas, tratamento em cantos e teste de posicao de caixas/ouvintes"
    if frequency_hz < 250:
        if issue == "gap":
            return "reposicionamento de caixas/ouvintes e absorcao banda larga com cuidado para nao matar a sala"
        return "absorcao banda larga profunda; se confirmado por medicao, considerar tratamento sintonizado"
    if frequency_hz < 700:
        return "absorcao de primeiras reflexoes, ajuste de posicao e verificacao com RT/IR"
    return "difusao, controle de reflexoes especulares e equilibrio entre absorcao e energia da sala"


def caution_for_frequency(frequency_hz: float) -> str:
    if frequency_hz < 250:
        return "confirmar com sweep/IR; modos dependem muito da posicao de fonte e microfone"
    if frequency_hz < 700:
        return "verificar com resposta ao impulso e RT; a fronteira entre modal e reflexivo e gradual"
    return "nao tratar como correcao modal pura; avaliar reflexoes, difusao e tempo de reverberacao"


def dominant_mode_type(modes: list[Mode]) -> str:
    counts = Counter(mode.classification for mode in modes)
    if not counts:
        return "nao identificado"
    labels = {
        "axial": "axial",
        "tangential": "tangencial",
        "oblique": "obliquo",
    }
    return labels[counts.most_common(1)[0][0]]


def rounded_mode_matches(modes: list[Mode], frequency: int) -> list[Mode]:
    return [mode for mode in modes if mode.rounded_hz == frequency]


def modes_in_range(modes: list[Mode], start_hz: float, end_hz: float) -> list[Mode]:
    return [mode for mode in modes if start_hz <= mode.frequency_hz <= end_hz]


def group_frequencies(frequencies: list[float], max_gap_hz: float) -> list[list[float]]:
    if not frequencies:
        return []

    groups: list[list[float]] = [[frequencies[0]]]
    for frequency in frequencies[1:]:
        if frequency - groups[-1][-1] <= max_gap_hz:
            groups[-1].append(frequency)
        else:
            groups.append([frequency])
    return groups


def group_frequencies_by_region(frequencies: list[float], max_gap_hz: float) -> list[list[float]]:
    if not frequencies:
        return []

    groups: list[list[float]] = [[frequencies[0]]]
    for frequency in frequencies[1:]:
        same_region = frequency_region_index(frequency) == frequency_region_index(groups[-1][-1])
        close_enough = frequency - groups[-1][-1] <= max_gap_hz
        if same_region and close_enough:
            groups[-1].append(frequency)
        else:
            groups.append([frequency])
    return groups


def format_frequency_range(group: list[float]) -> str:
    if len(group) == 1:
        return f"{group[0]:.0f} Hz"
    return f"{group[0]:.0f}-{group[-1]:.0f} Hz"


def recommendation_key(recommendation: AcousticRecommendation) -> tuple[str, str]:
    return recommendation.frequency, recommendation.likely_audible_effect


def acoustic_recommendations(room: Room, modes: list[Mode]) -> list[AcousticRecommendation]:
    recommendations: list[AcousticRecommendation] = []
    counts = counts_by_frequency(modes)

    clustered_frequencies = [
        frequency
        for frequency, counter in counts.items()
        if sum(counter.values()) >= 4
    ]
    for group in group_frequencies_by_region(clustered_frequencies, max_gap_hz=8):
        start, end = group[0], group[-1]
        matches = modes_in_range(modes, start - 0.5, end + 0.5)
        highest_count = max(sum(counts[int(frequency)].values()) for frequency in group)
        has_axial = any(mode.classification == "axial" for mode in matches)
        center = (start + end) / 2
        recommendations.append(
            AcousticRecommendation(
                frequency=format_frequency_range(group),
                mode_type=dominant_mode_type(matches),
                severity="alta" if has_axial or highest_count >= 6 else "media",
                likely_audible_effect=(
                    "agrupamento modal: faixa com maior chance de notas fortes, longas ou emboladas"
                ),
                suggested_treatment=treatment_for_frequency(center, "cluster"),
                caution=caution_for_frequency(center),
            )
        )

    axial_by_frequency = Counter(mode.rounded_hz for mode in modes if mode.classification == "axial")
    repeated_axials = [frequency for frequency, count in axial_by_frequency.items() if count > 1]
    for group in group_frequencies(sorted(repeated_axials), max_gap_hz=5):
        center = sum(group) / len(group)
        recommendations.append(
            AcousticRecommendation(
                frequency=format_frequency_range(group),
                mode_type="axial",
                severity="alta",
                likely_audible_effect="coincidencia axial: grave com maior risco de sobrar ou cancelar",
                suggested_treatment=treatment_for_frequency(center, "axial"),
                caution=caution_for_frequency(center),
            )
        )

    axial_modes = [mode for mode in modes if mode.classification == "axial"]
    low_axial_frequencies = sorted(mode.frequency_hz for mode in axial_modes if mode.frequency_hz < 80)
    for group in group_frequencies(low_axial_frequencies, max_gap_hz=6):
        center = sum(group) / len(group)
        recommendations.append(
            AcousticRecommendation(
                frequency=format_frequency_range(group),
                mode_type="axial",
                severity="alta" if center < 60 else "media",
                likely_audible_effect="modos axiais baixos: podem dominar notas graves proximas",
                suggested_treatment=treatment_for_frequency(center, "low"),
                caution=caution_for_frequency(center),
            )
        )

    low_modes = [mode for mode in modes if mode.frequency_hz < 80]
    if len(low_modes) >= 8:
        recommendations.append(
            AcousticRecommendation(
                frequency="< 80 Hz",
                mode_type=dominant_mode_type(low_modes),
                severity="alta",
                likely_audible_effect="acumulo de energia no grave profundo e maior variacao entre assentos",
                suggested_treatment="priorizar armadilhas de grave em cantos e testar posicao de caixas/ouvintes",
                caution="medir com sweep e comparar diferentes posicoes antes de escolher solucao sintonizada",
            )
        )

    sorted_freqs = sorted({mode.frequency_hz for mode in modes if mode.frequency_hz <= 300})
    for lower, upper in zip(sorted_freqs, sorted_freqs[1:]):
        gap = upper - lower
        if lower < 250 and gap >= 18:
            center = (lower + upper) / 2
            recommendations.append(
                AcousticRecommendation(
                    frequency=f"{lower:.1f}-{upper:.1f} Hz",
                    mode_type="lacuna",
                    severity="media" if gap < 30 else "alta",
                    likely_audible_effect="faixa com poucos modos: resposta pode parecer irregular entre notas vizinhas",
                    suggested_treatment=treatment_for_frequency(center, "gap"),
                    caution="lacunas mudam com posicao; confirmar medindo fonte e ouvinte reais",
                )
            )

    _, middle_ratio, longest_ratio = room_ratio(room)
    for warning in ratio_warnings(room, modes):
        if warning.severity in {"alto", "medio"}:
            recommendations.append(
                AcousticRecommendation(
                    frequency=f"proporcao 1:{middle_ratio:.2f}:{longest_ratio:.2f}",
                    mode_type="geometria da sala",
                    severity="alta" if warning.severity == "alto" else "media",
                    likely_audible_effect=warning.message,
                    suggested_treatment="reposicionamento de caixas/ouvintes; tratamento de graves e absorcao conforme medicao",
                    caution="proporcao ruim nao e corrigida so com material fino; medir antes de intervir pesado",
                )
            )

    unique: dict[tuple[str, str], AcousticRecommendation] = {}
    for recommendation in recommendations:
        unique.setdefault(recommendation_key(recommendation), recommendation)

    severity_order = {"alta": 0, "media": 1, "baixa": 2}

    def sort_key(item: AcousticRecommendation) -> tuple[int, float]:
        digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in item.frequency)
        first_number = float(digits.split()[0]) if digits.split() else 9999.0
        return severity_order.get(item.severity, 3), first_number

    return sorted(unique.values(), key=sort_key)


def export_acoustic_recommendations(room: Room, modes: list[Mode], path: Path) -> list[AcousticRecommendation]:
    recommendations = acoustic_recommendations(room, modes)
    ratios = room_ratio(room)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        file.write("Relatorio de recomendacoes acusticas\n")
        file.write("====================================\n\n")
        file.write("Este relatorio e didatico e usa apenas um modelo preditivo de modos de sala retangular.\n")
        file.write(
            "Ele nao deve ser lido como prescricao definitiva de engenharia acustica. "
            "Na pratica, confirme as hipoteses com medicoes da sala, como sweep senoidal, "
            "resposta ao impulso, analise de RT/EDT e medicoes em diferentes posicoes de escuta.\n\n"
        )
        file.write(f"Dimensoes analisadas: {room.length:g} x {room.width:g} x {room.height:g} m\n")
        file.write(f"Proporcao normalizada: 1:{ratios[1]:.2f}:{ratios[2]:.2f}\n")
        file.write(f"Velocidade do som estimada: {room.speed_of_sound:.2f} m/s\n")
        file.write(f"Total de modos calculados: {len(modes)}\n\n")

        file.write("Faixas de leitura usadas\n")
        file.write("------------------------\n")
        file.write("- Abaixo de 80 Hz: grave muito baixo; prioridade para armadilhas de grave.\n")
        file.write("- 80 a 250 Hz: regiao modal grave/medio-grave; absorcao banda larga ou tratamento sintonizado.\n")
        file.write("- 250 a 700 Hz: regiao de transicao; absorcao, posicionamento e analise de reflexoes.\n")
        file.write("- Acima de 700 Hz: menos dominada por modos; considerar difusao e controle de reflexoes.\n\n")

        file.write("Resumo por frequencia critica\n")
        file.write("-----------------------------\n\n")
        file.write("| frequency | mode type | severity | likely audible effect | suggested treatment | caution |\n")
        file.write("| --- | --- | --- | --- | --- | --- |\n")
        for item in recommendations:
            file.write(
                f"| {item.frequency} | {item.mode_type} | {item.severity} | "
                f"{item.likely_audible_effect} | {item.suggested_treatment} | {item.caution} |\n"
            )

        file.write("\nComentarios didaticos\n")
        file.write("---------------------\n")
        file.write(
            "Modos axiais costumam ser percebidos com mais forca porque envolvem duas superficies opostas. "
            "Quando dois modos aparecem na mesma frequencia, a sala pode reforcar muito uma nota ou criar "
            "cancelamentos fortes dependendo da posicao do ouvinte.\n\n"
        )
        file.write(
            "Armadilhas de grave ajudam mais quando sao profundas, instaladas em regioes de alta pressao, "
            "como cantos e encontros entre paredes. Paineis finos geralmente nao resolvem problemas abaixo "
            "de 80 Hz.\n\n"
        )
        file.write(
            "Entre 80 e 250 Hz, absorcao de banda larga mais espessa pode ajudar, mas alguns problemas muito "
            "estreitos podem exigir tratamento sintonizado. Esse tipo de decisao deve ser tomada com medicao.\n\n"
        )
        file.write(
            "Acima da regiao modal principal, difusao e controle de primeiras reflexoes podem melhorar clareza, "
            "imagem estereo e conforto, mas isso ja nao e simplesmente 'corrigir modos'.\n"
        )

    return recommendations


def _max_index(dimension_m: float, max_frequency_hz: float, speed_of_sound: float) -> int:
    return int(math.ceil(2.0 * max_frequency_hz * dimension_m / speed_of_sound))


def calculate_modes(room: Room, max_frequency_hz: float = 300.0) -> list[Mode]:
    """Return all unique room modes at or below max_frequency_hz."""
    max_p = _max_index(room.length, max_frequency_hz, room.speed_of_sound)
    max_q = _max_index(room.width, max_frequency_hz, room.speed_of_sound)
    max_r = _max_index(room.height, max_frequency_hz, room.speed_of_sound)

    modes: list[Mode] = []
    for p in range(max_p + 1):
        for q in range(max_q + 1):
            for r in range(max_r + 1):
                if p == q == r == 0:
                    continue

                frequency = modal_frequency(room, p, q, r)
                if frequency <= max_frequency_hz:
                    modes.append(
                        Mode(
                            p=p,
                            q=q,
                            r=r,
                            frequency_hz=frequency,
                            rounded_hz=round(frequency),
                            classification=classify_mode(p, q, r),
                        )
                    )

    return sorted(modes, key=lambda mode: (mode.frequency_hz, mode.classification, mode.p, mode.q, mode.r))


def export_modes_csv(modes: Iterable[Mode], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("p", "q", "r", "frequency_hz", "rounded_hz", "classification"))
        for mode in modes:
            writer.writerow(
                (
                    mode.p,
                    mode.q,
                    mode.r,
                    f"{mode.frequency_hz:.6f}",
                    mode.rounded_hz,
                    mode.classification,
                )
            )


def export_summary_csv(room: Room, modes: list[Mode], path: Path) -> None:
    counts = Counter(mode.classification for mode in modes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("metric", "value"))
        writer.writerow(("length_m", room.length))
        writer.writerow(("width_m", room.width))
        writer.writerow(("height_m", room.height))
        writer.writerow(("temperature_c", room.temperature_c))
        writer.writerow(("speed_of_sound_m_s", f"{room.speed_of_sound:.6f}"))
        writer.writerow(("volume_m3", f"{room.volume:.6f}"))
        writer.writerow(("surface_area_m2", f"{room.surface_area:.6f}"))
        writer.writerow(("spreadsheet_schroeder_label_hz", f"{room.spreadsheet_schroeder_label:.6f}"))
        writer.writerow(("normalized_ratio", ":".join(f"{value:.3f}" for value in room_ratio(room))))
        writer.writerow(("total_modes", len(modes)))
        writer.writerow(("axial_modes", counts["axial"]))
        writer.writerow(("tangential_modes", counts["tangential"]))
        writer.writerow(("oblique_modes", counts["oblique"]))


def export_warnings(room: Room, modes: list[Mode], path: Path) -> list[RatioWarning]:
    warnings = ratio_warnings(room, modes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        file.write("Avisos sobre proporcoes da sala\n")
        file.write("===============================\n\n")
        file.write(f"Proporcao normalizada: 1:{room_ratio(room)[1]:.2f}:{room_ratio(room)[2]:.2f}\n\n")
        for warning in warnings:
            file.write(f"[{warning.severity}] {warning.message}\n")
    return warnings


def counts_by_frequency(modes: Iterable[Mode]) -> dict[int, Counter[str]]:
    counts: dict[int, Counter[str]] = defaultdict(Counter)
    for mode in modes:
        counts[mode.rounded_hz][mode.classification] += 1
    return dict(sorted(counts.items()))


def band_edges(center_hz: float) -> tuple[float, float]:
    ratio = 2.0 ** (1.0 / 6.0)
    return center_hz / ratio, center_hz * ratio


def band_range_label(center_hz: float) -> str:
    low, high = band_edges(center_hz)
    return f"{low:.1f}-{high:.1f}" if low < 10 else f"{round(low)}-{round(high)}"


def counts_by_band(modes: Iterable[Mode], bands: Iterable[float] = DEFAULT_BANDS) -> dict[float, Counter[str]]:
    result: dict[float, Counter[str]] = {}
    for band in bands:
        low, high = band_edges(band)
        counter: Counter[str] = Counter()
        for mode in modes:
            if low <= mode.frequency_hz < high:
                counter[mode.classification] += 1
        result[band] = counter
    return result


def weighted_modal_density_by_band(modes: Iterable[Mode], bands: Iterable[float] = DEFAULT_BANDS) -> dict[float, float]:
    densities: dict[float, float] = {}
    modes = list(modes)
    for band in bands:
        low, high = band_edges(band)
        weighted_total = 0.0
        for mode in modes:
            if low <= mode.frequency_hz < high:
                # Weighting lowers tangential and oblique influence to match
                # the behavior of the original spreadsheet more closely.
                weighted_total += MODAL_DENSITY_WEIGHTS[mode.classification]
        densities[band] = weighted_total / band
    return densities


def modal_density_tick_step(max_density: float) -> float:
    if max_density <= 0.5:
        return 0.05
    if max_density <= 1.0:
        return 0.1
    if max_density <= 2.0:
        return 0.2
    if max_density <= 5.0:
        return 0.5
    return float(math.ceil(max_density / 8.0))


def mode_count_tick_step(max_count: int) -> int:
    if max_count <= 6:
        return 1
    if max_count <= 12:
        return 2
    if max_count <= 30:
        return 5
    if max_count <= 60:
        return 10
    return int(math.ceil(max_count / 6.0 / 10.0) * 10)


def export_band_csv(modes: list[Mode], path: Path, bands: Iterable[float] = DEFAULT_BANDS) -> None:
    band_counts = counts_by_band(modes, bands)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("band_hz", "axial", "tangential", "oblique", "total", "modal_density"))
        for band, counts in band_counts.items():
            total = counts["axial"] + counts["tangential"] + counts["oblique"]
            writer.writerow(
                (
                    band,
                    counts["axial"],
                    counts["tangential"],
                    counts["oblique"],
                    total,
                    f"{total / band:.6f}",
                )
            )


def plot_frequency_counts(modes: list[Mode], path: Path) -> None:
    counts = counts_by_frequency(modes)
    frequencies = list(counts)
    axial = [counts[f]["axial"] for f in frequencies]
    tangential = [counts[f]["tangential"] for f in frequencies]
    oblique = [counts[f]["oblique"] for f in frequencies]

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(frequencies, axial, label="Axiais", linewidth=1.6, color=MODE_COLORS["axial"])
    ax.plot(frequencies, tangential, label="Tangenciais", linewidth=1.6, color=MODE_COLORS["tangential"])
    ax.plot(frequencies, oblique, label="Obliquos", linewidth=1.6, color=MODE_COLORS["oblique"])
    ax.set_title("Modos por Frequência")
    ax.set_xlabel("Frequência (Hz)")
    ax.set_ylabel("Número de modos")
    ax.set_xlim(left=0)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_modal_distribution(modes: list[Mode], path: Path) -> None:
    y_positions = {"axial": 3, "tangential": 2, "oblique": 1}
    labels = {3: "Axiais", 2: "Tangenciais", 1: "Obliquos"}

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 4.8))
    for classification in ("axial", "tangential", "oblique"):
        frequencies = [mode.frequency_hz for mode in modes if mode.classification == classification]
        y = [y_positions[classification]] * len(frequencies)
        ax.scatter(
            frequencies,
            y,
            s=24,
            alpha=0.75,
            label=labels[y_positions[classification]],
            color=MODE_COLORS[classification],
            edgecolors="none",
        )

    ax.set_title("Distribuicao dos modos por tipo")
    ax.set_xlabel("Frequencia (Hz)")
    ax.set_yticks(list(labels))
    ax.set_yticklabels([labels[value] for value in labels])
    ax.set_ylim(0.4, 3.6)
    ax.grid(axis="x", alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_band_counts(modes: list[Mode], path: Path, bands: Iterable[float] = DEFAULT_BANDS) -> None:
    band_counts = counts_by_band(modes, bands)
    labels = [band_range_label(band) for band in band_counts]
    axial = [counts["axial"] for counts in band_counts.values()]
    tangential = [counts["tangential"] for counts in band_counts.values()]
    oblique = [counts["oblique"] for counts in band_counts.values()]
    totals = [a + t + o for a, t, o in zip(axial, tangential, oblique)]
    max_count = max([1, *totals])
    tick_step = mode_count_tick_step(max_count)
    y_max = max(tick_step, math.ceil(max_count / tick_step) * tick_step)
    tick_count = round(y_max / tick_step)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, axial, label="Axiais", color=MODE_COLORS["axial"])
    ax.bar(labels, tangential, bottom=axial, label="Tangenciais", color=MODE_COLORS["tangential"])
    bottoms = [a + t for a, t in zip(axial, tangential)]
    ax.bar(labels, oblique, bottom=bottoms, label="Obliquos", color=MODE_COLORS["oblique"])
    ax.set_title("Modos por Banda")
    ax.set_xlabel("Banda de frequência (Hz)")
    ax.set_ylabel("Número de modos")
    ax.set_ylim(0, y_max)
    ax.set_yticks([i * tick_step for i in range(tick_count + 1)])
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def plot_modal_density(modes: list[Mode], path: Path, bands: Iterable[float] = DEFAULT_BANDS) -> None:
    density_by_band = weighted_modal_density_by_band(modes, bands)
    labels = [str(band) for band in density_by_band]
    densities = list(density_by_band.values())
    max_density = max([0.01, *densities])
    tick_step = modal_density_tick_step(max_density)
    y_max = max(tick_step, math.ceil(max_density / tick_step) * tick_step)
    tick_count = round(y_max / tick_step)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(labels, densities, marker="o", color="#8b5a9f")
    ax.set_title("Densidade Modal Ponderada")
    ax.set_xlabel("Banda de frequência (Hz)")
    ax.set_ylabel("Densidade modal ponderada")
    ax.set_ylim(0, y_max)
    ax.set_yticks([i * tick_step for i in range(tick_count + 1)])
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def generate_outputs(room: Room, output_dir: Path, max_frequency_hz: float = 300.0) -> list[Mode]:
    modes = calculate_modes(room, max_frequency_hz)

    export_modes_csv(modes, output_dir / "modes.csv")
    export_summary_csv(room, modes, output_dir / "summary.csv")
    export_band_csv(modes, output_dir / "bands.csv")
    export_warnings(room, modes, output_dir / "warnings.txt")
    export_acoustic_recommendations(room, modes, output_dir / "acoustic_recommendations.txt")
    plot_frequency_counts(modes, output_dir / "modal_plot.png")
    plot_modal_distribution(modes, output_dir / "modal_distribution.png")
    plot_band_counts(modes, output_dir / "modes_by_band.png")
    plot_modal_density(modes, output_dir / "modal_density.png")

    return modes


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Calcula modos acusticos de uma sala retangular.")
    parser.add_argument("--length", "-l", type=positive_float, help="room length in meters")
    parser.add_argument("--width", "-w", type=positive_float, help="room width in meters")
    parser.add_argument("--height", "-H", type=positive_float, help="room height in meters")
    parser.add_argument(
        "--example",
        choices=sorted(EXAMPLE_ROOMS),
        help="use a built-in example room: small, studio, or concert",
    )
    parser.add_argument("--temperature", "-t", type=float, default=24.0, help="air temperature in Celsius")
    parser.add_argument("--max-frequency", "-f", type=positive_float, default=300.0, help="maximum frequency in Hz")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path(__file__).resolve().parent / "outputs",
        help="directory for CSV and PNG outputs",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.example:
        length, width, height = EXAMPLE_ROOMS[args.example]
    else:
        missing = [
            name
            for name, value in (
                ("--length", args.length),
                ("--width", args.width),
                ("--height", args.height),
            )
            if value is None
        ]
        if missing:
            raise SystemExit(f"Missing required dimensions: {', '.join(missing)}")
        length, width, height = args.length, args.width, args.height

    room = Room(length, width, height, args.temperature)
    modes = generate_outputs(room, args.output_dir, args.max_frequency)

    counts = Counter(mode.classification for mode in modes)
    warnings = ratio_warnings(room, modes)
    print(f"Output directory: {args.output_dir}")
    print(f"Room: {room.length:g} m x {room.width:g} m x {room.height:g} m")
    print(f"Normalized ratio: 1:{room_ratio(room)[1]:.2f}:{room_ratio(room)[2]:.2f}")
    print(f"Speed of sound: {room.speed_of_sound:.3f} m/s")
    print(f"Modes <= {args.max_frequency:g} Hz: {len(modes)}")
    print(f"  axial: {counts['axial']}")
    print(f"  tangential: {counts['tangential']}")
    print(f"  oblique: {counts['oblique']}")
    print("Warnings:")
    for warning in warnings:
        print(f"  [{warning.severity}] {warning.message}")


if __name__ == "__main__":
    main()
