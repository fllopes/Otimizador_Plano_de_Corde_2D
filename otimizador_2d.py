"""
Woodworking Cut List Optimizer (2D Heterogeneous Bin Packing)
-------------------------------------------------------------
This script calculates the most efficient way to cut a list of rectangular 
parts from multiple heterogeneous raw material boards. It accounts for saw 
blade thickness (kerf), part rotation, inventory limits, and material costs.

Includes dynamic Edge Banding (Fita de Borda) reduction logic, 
multi-objective optimization (Dual, Geometric, and Financial modes),
and customized HTML report generation with personalized contact info.

Optimization Method: 
Monte Carlo randomized iterations using a First-Fit Decreasing (FFD) 
heuristic with a Binary Tree Shortest-Axis-Split.

Author: Filipe Lopes
AI Assistance: Code generated with the assistance of Google Gemini
Date: November 2026
"""

__author__ = "Filipe Lopes"
__credits__ = ["Filipe Lopes", "Google Gemini (AI)"]
__version__ = "3.0.0"
__maintainer__ = "Filipe Lopes"

import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Default Fallback Configuration ---
DEFAULT_RAW_WIDTH = 2750
DEFAULT_RAW_LENGTH = 1830
DEFAULT_KERF = 3


@dataclass(frozen=True)
class UserContactInfo:
    """Stores user personal details to populate report headers and footers."""
    name: str
    phone: str
    email: str


@dataclass(frozen=True)
class RawBoardSpec:
    """Represents a raw material stock dimension, saw kerf, available inventory, and price."""
    id: str
    length: int
    width: int
    thickness: int
    name: str
    kerf: int
    qty: int
    price: float


@dataclass(frozen=True)
class Part:
    """Represents a single piece to be cut for the project."""
    function: str
    width: int
    length: int
    thickness: int
    qty: int
    material_refs: Tuple[str, ...]
    can_rotate: bool


@dataclass(frozen=True)
class PlacedPart:
    """Represents a part that has been successfully positioned on a specific board layout."""
    function: str
    x: int
    y: int
    w: int
    h: int
    rotated: bool


class Node:
    """
    A binary tree node representing an area of space on a raw material board.
    Tracks usage status and child sub-regions after splitting.
    """
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.used = False
        self.right: Optional['Node'] = None
        self.down: Optional['Node'] = None


class Packer:
    """
    2D Binary Tree Packer.
    Manages spatial placement of rectangular parts within a target board boundary.
    """
    def __init__(self, width: int, height: int, board_spec: RawBoardSpec):
        self.width = width
        self.height = height
        self.board_spec = board_spec
        self.root = Node(0, 0, width, height)
        self.placed_parts: List[PlacedPart] = []

    def fit(self, w: int, h: int, function_name: str) -> Optional[Node]:
        """Attempts to find and split an available node for a given part width and height."""
        node = self.find_node(self.root, w, h)
        if node:
            return self.split_node(node, w, h, function_name)
        return None

    def find_node(self, root: Node, w: int, h: int) -> Optional[Node]:
        """Recursively traverses the binary tree to find an unused node with sufficient capacity."""
        if root.used:
            return self.find_node(root.right, w, h) or self.find_node(root.down, w, h)
        elif w <= root.w and h <= root.h:
            return root
        return None

    def split_node(self, node: Node, w: int, h: int, function_name: str) -> Node:
        """
        Splits remaining empty space using the Shortest-Axis-Split heuristic
        to maximize contiguous reusable area and reduce unusable slivers.
        """
        node.used = True
        dw = node.w - w
        dh = node.h - h

        if dw > dh:
            node.down = Node(node.x, node.y + h, w, dh)
            node.right = Node(node.x + w, node.y, dw, node.h)
        else:
            node.down = Node(node.x, node.y + h, node.w, dh)
            node.right = Node(node.x + w, node.y, dw, h)

        return node


def parse_positive_int(value: str, field_name: str, line_idx: int, errors: List[str]) -> int:
    """Parses a string into a positive integer (>0). Records error details on failure."""
    try:
        val = int(value.strip())
        if val <= 0:
            errors.append(f"Linha {line_idx}: '{field_name}' deve ser maior que zero (encontrado: '{val}').")
            return 0
        return val
    except ValueError:
        errors.append(f"Linha {line_idx}: '{field_name}' inválido. Esperado um inteiro (encontrado: '{value.strip()}').")
        return 0


def parse_positive_float(value: str, field_name: str, line_idx: int, errors: List[str]) -> float:
    """Parses a string into a non-negative float (>=0). Supports comma and dot decimals."""
    try:
        val = float(value.strip().replace(',', '.'))
        if val < 0:
            errors.append(f"Linha {line_idx}: '{field_name}' não pode ser negativo (encontrado: '{val}').")
            return 0.0
        return val
    except ValueError:
        errors.append(f"Linha {line_idx}: '{field_name}' inválido. Esperado um número (encontrado: '{value.strip()}').")
        return 0.0


def normalize_headers(headers: List[str]) -> List[str]:
    """Cleans CSV headers by removing leading/trailing spaces and converting to lowercase."""
    return [h.strip().lower() for h in headers if h]


def read_raw_materials_csv(file_path: Path) -> Dict[str, RawBoardSpec]:
    """Reads, validates, and indexes raw material board stock specifications from CSV."""
    raw_materials = {}
    errors = []

    try:
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            raw_headers = f.readline().strip().split(';')
            headers = normalize_headers(raw_headers)
            
            f.seek(0)
            reader = csv.DictReader(f, fieldnames=headers, delimiter=";")
            next(reader, None)  # Skip header row

            for line_idx, row in enumerate(reader, start=2):
                if not any(row.values()): 
                    continue

                # Ignore commented rows starting with '//'
                first_val = str(list(row.values())[0] or "").strip()
                if first_val.startswith('//'):
                    continue

                raw_id = row.get("id", "").strip()
                if not raw_id:
                    errors.append(f"Linha {line_idx}: Coluna 'id' não encontrada ou vazia.")
                    continue

                length = parse_positive_int(row.get("comprimento", "0"), "Comprimento", line_idx, errors)
                width = parse_positive_int(row.get("largura", "0"), "Largura", line_idx, errors)
                thickness = parse_positive_int(row.get("profundidade", "0"), "Profundidade", line_idx, errors)
                name = row.get("materia_prima", "").strip()

                kerf_val = row.get("largura_corte", "").strip()
                kerf = parse_positive_int(kerf_val, "Largura do Corte", line_idx, errors) if kerf_val else DEFAULT_KERF
                
                qty_val = row.get("qtd", row.get("qtd_inventario", "")).strip()
                qty = parse_positive_int(qty_val, "Qtd Inventário", line_idx, errors) if qty_val else sys.maxsize

                price_val = row.get("custo_unidade", row.get("preco", "")).strip()
                price = parse_positive_float(price_val, "Custo Unidade", line_idx, errors) if price_val else 0.0

                if not errors:
                    raw_materials[raw_id] = RawBoardSpec(
                        id=raw_id, length=length, width=width, 
                        thickness=thickness, name=name, kerf=kerf, qty=qty, price=price
                    )
    except IOError as e:
        sys.exit(f"\n[ERRO CRÍTICO] Falha ao ler matérias-primas:\n{str(e)}")

    if errors:
        print(f"\n[ERRO] Problemas no arquivo '{file_path.name}':")
        for err in errors: 
            print(f"  - {err}")
        sys.exit(1)

    return raw_materials


def read_cut_list_csv(file_path: Path) -> List[Part]:
    """Reads, validates, and applies edge banding deductions to project parts from CSV."""
    parts = []
    errors = []

    try:
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            raw_headers = f.readline().strip().split(';')
            headers = normalize_headers(raw_headers)
            
            f.seek(0)
            reader = csv.DictReader(f, fieldnames=headers, delimiter=";")
            next(reader, None)

            for line_idx, row in enumerate(reader, start=2):
                if not any(row.values()): 
                    continue

                # Ignore commented rows starting with '//'
                first_val = str(list(row.values())[0] or "").strip()
                if first_val.startswith('//'):
                    continue

                qty = parse_positive_int(row.get("quantidade", "0"), "Quantidade", line_idx, errors)
                length = parse_positive_int(row.get("comprimento", "0"), "Comprimento", line_idx, errors)
                width = parse_positive_int(row.get("largura", "0"), "Largura", line_idx, errors)
                thickness = parse_positive_int(row.get("profundidade", "0"), "Profundidade", line_idx, errors)
                
                function = row.get("função", row.get("funcao", "")).strip()
                
                raw_mat_val = row.get("material", "").strip()
                material_refs = tuple(m.strip() for m in raw_mat_val.split(",") if m.strip())

                if not function: 
                    errors.append(f"Linha {line_idx}: Coluna 'Função' ausente ou vazia.")
                if not material_refs: 
                    errors.append(f"Linha {line_idx}: Coluna 'Material' ausente ou vazia.")

                girar_val = row.get("girar", "").strip().lower()
                can_rotate = girar_val in ["sim", "yes", "s", "y"]

                # Edge Banding deduction logic
                banding_str = row.get("espessura da fita", row.get("espessura_da_fita", "0")).strip()
                banding = int(banding_str) if banding_str.isdigit() else 0
                
                c1 = row.get("fita_c1", "").strip().lower() == "x"
                c2 = row.get("fita_c2", "").strip().lower() == "x"
                l1 = row.get("fita_l1", "").strip().lower() == "x"
                l2 = row.get("fita_l2", "").strip().lower() == "x"
                
                if banding > 0:
                    if c1: length -= banding
                    if c2: length -= banding
                    if l1: width -= banding
                    if l2: width -= banding
                    
                    if length <= 0 or width <= 0:
                        errors.append(f"Linha {line_idx}: A espessura da fita reduziu a dimensão da peça a zero ou menos.")

                if not errors:
                    parts.append(Part(
                        function=function, width=width, length=length,
                        thickness=thickness, qty=qty, material_refs=material_refs, can_rotate=can_rotate
                    ))
    except IOError as e:
        sys.exit(f"\n[ERRO CRÍTICO] Falha ao ler lista de corte:\n{str(e)}")

    if errors:
        print(f"\n[ERRO] Problemas no arquivo '{file_path.name}':")
        for err in errors: 
            print(f"  - {err}")
        sys.exit(1)

    return parts


def run_single_pass(group_parts: List[Part], group_specs: List[RawBoardSpec]) -> List[Packer]:
    """Executes a single deterministic bin-packing pass for an ordered list of parts."""
    boards: List[Packer] = []
    board_usage = {spec.id: 0 for spec in group_specs}

    for part in group_parts:
        placed = False

        for board in boards:
            if board.board_spec.id not in part.material_refs: 
                continue
            
            kerf = board.board_spec.kerf
            padded_w = part.length + kerf
            padded_l = part.width + kerf

            node = board.fit(padded_w, padded_l, part.function)
            if node:
                board.placed_parts.append(PlacedPart(part.function, node.x, node.y, part.length, part.width, False))
                placed = True
                break
            elif part.can_rotate:
                node = board.fit(padded_l, padded_w, part.function)
                if node:
                    board.placed_parts.append(PlacedPart(part.function, node.x, node.y, part.width, part.length, True))
                    placed = True
                    break

        if not placed:
            for spec in group_specs:
                if spec.id not in part.material_refs: 
                    continue
                if board_usage[spec.id] >= spec.qty: 
                    continue
                
                kerf = spec.kerf
                padded_w = part.length + kerf
                padded_l = part.width + kerf
                
                new_board = Packer(spec.length + kerf, spec.width + kerf, spec)
                node = new_board.fit(padded_w, padded_l, part.function)
                
                if node:
                    new_board.placed_parts.append(PlacedPart(part.function, node.x, node.y, part.length, part.width, False))
                    boards.append(new_board)
                    board_usage[spec.id] += 1
                    placed = True
                    break
                elif part.can_rotate:
                    node = new_board.fit(padded_l, padded_w, part.function)
                    if node:
                        new_board.placed_parts.append(PlacedPart(part.function, node.x, node.y, part.width, part.length, True))
                        boards.append(new_board)
                        board_usage[spec.id] += 1
                        placed = True
                        break

        if not placed:
            return []

    return boards


def evaluate_layout_quality(boards: List[Packer], mode: str) -> Tuple:
    """Computes a comparable score tuple for a layout candidate based on optimization mode."""
    if not boards: 
        return (float('inf'), float('inf'), float('inf'))
    
    total_area = sum(b.board_spec.length * b.board_spec.width for b in boards)
    total_cost = sum(b.board_spec.price for b in boards)
    
    if mode == 'G':
        return (total_area, len(boards), total_cost)
    elif mode == 'F':
        return (total_cost, 0, 0)
    else:
        return (total_cost, total_area, len(boards))


def optimize_cuts(parts: List[Part], raw_materials: Dict[str, RawBoardSpec], iterations: int, mode: str) -> Dict[str, List[Packer]]:
    """Runs Monte Carlo randomized iterations to discover the best-fitting layout."""
    groups: Dict[Tuple[str, int], List[Part]] = {}
    for part in parts:
        primary_id = part.material_refs[0]
        if primary_id in raw_materials:
            spec = raw_materials[primary_id]
            group_key = (spec.name, spec.thickness)
        else:
            group_key = ("Desconhecido", part.thickness)
        
        if group_key not in groups: 
            groups[group_key] = []
        for _ in range(part.qty):
            groups[group_key].append(part)

    results: Dict[str, List[Packer]] = {}

    for (mat_name, mat_thick), group_parts in groups.items():
        group_spec_ids = set()
        for p in group_parts:
            group_spec_ids.update(p.material_refs)
        
        group_specs = [raw_materials[sid] for sid in group_spec_ids if sid in raw_materials]

        for p in set(group_parts):
            fits_any = False
            for ref in p.material_refs:
                if ref in raw_materials:
                    spec = raw_materials[ref]
                    if (p.length <= spec.length and p.width <= spec.width) or \
                       (p.can_rotate and p.length <= spec.width and p.width <= spec.length):
                        fits_any = True
                        break
            if not fits_any:
                sys.exit(f"\n[ERRO CRÍTICO] A peça '{p.function}' ({p.length}x{p.width}mm) é maior que TODAS as chapas permitidas (IDs {p.material_refs}). Impossível cortar.")

        best_boards: List[Packer] = []
        best_score = (float("inf"), float("inf"), float("inf"))

        for i in range(iterations):
            candidate_parts = list(group_parts)
            
            if i == 0: 
                candidate_parts.sort(key=lambda p: p.width * p.length, reverse=True)
            elif i == 1: 
                candidate_parts.sort(key=lambda p: max(p.width, p.length), reverse=True)
            else: 
                candidate_parts.sort(key=lambda p: (p.width * p.length) * random.uniform(0.75, 1.25), reverse=True)

            if i % 3 == 0: 
                current_specs = sorted(group_specs, key=lambda s: s.length * s.width, reverse=True)
            elif i % 3 == 1: 
                current_specs = sorted(group_specs, key=lambda s: s.length * s.width, reverse=False)
            else:
                current_specs = list(group_specs)
                random.shuffle(current_specs)

            boards = run_single_pass(candidate_parts, current_specs)
            
            if boards:
                score = evaluate_layout_quality(boards, mode)
                if score < best_score:
                    best_score = score
                    best_boards = boards

        if not best_boards:
             sys.exit(f"\n[ERRO CRÍTICO] Não foi possível encontrar um encaixe para o material '{mat_name}'. Verifique se possui quantidade suficiente de chapas brutas.")

        group_title = f"{mat_name.title()} ({mat_thick}mm)"
        results[group_title] = best_boards

    return results


def format_brl(value: float) -> str:
    """Formats a floating-point number into Brazilian Real currency string (R$ 1.234,56)."""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generate_html_report(results: Dict[str, List[Packer]], output_path: Path, mode_str: str, iterations: int, user_info: UserContactInfo):
    """Generates an executive-ready HTML document populated with the user's custom contact details."""
    
    grand_total = 0.0
    usage_data = []

    for group_title, boards in results.items():
        usage = {}
        for b in boards:
            usage[b.board_spec] = usage.get(b.board_spec, 0) + 1
        
        for spec, count in usage.items():
            subtotal = count * spec.price
            grand_total += subtotal
            usage_data.append((count, group_title, spec, subtotal))

    # Format header contact block dynamically based on user input
    contact_header_html = f"<strong>Nome:</strong> {user_info.name}<br>" if user_info.name else ""
    if user_info.phone:
        contact_header_html += f"<strong>Telefone:</strong> {user_info.phone}<br>"
    if user_info.email:
        contact_header_html += f"<strong>E-mail:</strong> {user_info.email}"

    # Format footer dynamically
    footer_parts = []
    if user_info.name:
        footer_parts.append(f"Plano de Corte gerado para <strong>{user_info.name}</strong>")
    else:
        footer_parts.append("Plano de Corte Gerado")
    if user_info.phone:
        footer_parts.append(f"Contato: <strong>{user_info.phone}</strong>")
    if user_info.email:
        footer_parts.append(f"<strong>{user_info.email}</strong>")

    footer_html = " | ".join(footer_parts)

    html_template = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plano de Corte - Otimizado</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --sand: #FDFBF7; --sand-dark: #F3EFE9; --wood: #8C6D46; --terra: #B85B35; --navy: #1D2A3A; --border: #E5DFD5; }}
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background-color: #E8E8E8; color: var(--navy); margin: 0; padding: 20px; font-size: 13px; }}
        .page-container {{ max-width: 800px; margin: 0 auto; background-color: #FFFFFF; padding: 40px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); border-top: 6px solid var(--wood); border-radius: 4px; }}
        
        header {{ border-bottom: 2px solid var(--sand-dark); padding-bottom: 25px; margin-bottom: 25px; }}
        .header-titles {{ margin-bottom: 25px; }}
        .header-titles h1 {{ color: var(--wood); font-size: 26px; margin: 0 0 5px 0; text-transform: uppercase; letter-spacing: 1px; }}
        .header-titles h2 {{ color: var(--terra); font-size: 15px; margin: 0; font-weight: 500; }}
        
        .header-details {{ display: flex; justify-content: space-between; align-items: center; }}
        .contact-info {{ font-size: 14px; line-height: 1.5; }}
        .contact-info strong {{ color: var(--wood); }}
        
        .total-price-box {{ border: 2px solid var(--border); background-color: var(--sand-dark); padding: 15px 25px; border-radius: 6px; text-align: center; display: flex; flex-direction: column; justify-content: center; min-width: 180px; }}
        .total-price-box span.title {{ font-size: 11px; text-transform: uppercase; font-weight: 700; color: var(--wood); letter-spacing: 0.5px; margin-bottom: 5px; }}
        .total-price-box span.value {{ font-size: 20px; font-weight: 700; color: var(--navy); }}

        .opt-summary {{ background-color: var(--sand); border: 1px solid var(--border); padding: 12px 15px; border-radius: 4px; margin-bottom: 20px; font-size: 13px; color: var(--navy); }}
        .opt-summary strong {{ color: var(--wood); }}

        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background-color: var(--sand-dark); color: var(--wood); font-weight: 700; text-transform: uppercase; font-size: 11px; }}
        .col-qtd {{ text-align: center; font-weight: 700; color: var(--terra); font-size: 14px; }}
        .section-title {{ color: var(--navy); font-size: 18px; border-bottom: 2px solid var(--terra); padding-bottom: 5px; margin-top: 40px; margin-bottom: 20px; }}
        .board-container {{ margin-bottom: 40px; page-break-inside: avoid; }}
        .board-header {{ font-weight: 700; margin-bottom: 10px; color: var(--wood); font-size: 15px; }}
        svg text {{ font-family: 'Inter', sans-serif; pointer-events: none; }}
        footer {{ background-color: var(--sand-dark); padding: 15px 20px; text-align: center; border-radius: 4px; margin-top: 30px; border: 1px solid var(--border); }}
        footer p {{ margin: 0; font-size: 13px; font-weight: 500; }}
        footer strong {{ color: var(--terra); }}
        
        @media print {{
            body {{ background-color: #FFF; padding: 0; }}
            .page-container {{ box-shadow: none; margin: 0; padding: 10mm; max-width: 100%; border-top: none; }}
            .page-break {{ page-break-before: always; }}
            @page {{ size: A4; margin: 0; }}
        }}
    </style>
</head>
<body>
    <div class="page-container">
        <header>
            <div class="header-titles">
                <h1>Plano de Corte Otimizado</h1>
                <h2>Relatório de Fabricação</h2>
            </div>
            <div class="header-details">
                <div class="contact-info">
                    {contact_header_html}
                </div>
                <div class="total-price-box">
                    <span class="title">Custo Material</span>
                    <span class="value">R$ {format_brl(grand_total)}</span>
                </div>
            </div>
        </header>

        <h2 class="section-title">Resumo de Material Necessário (Lista de Compras)</h2>
        
        <div class="opt-summary">
            <strong>Modo de Otimização:</strong> {mode_str} <span style="margin: 0 10px; color: var(--border);">|</span>
            <strong>Profundidade (Iterações):</strong> {iterations:,}
        </div>

        <table>
            <thead>
                <tr>
                    <th style="text-align: center;">Qtd Usada</th>
                    <th>Material (ID)</th>
                    <th>Dimensão (mm)</th>
                    <th>Custo Unit. (R$)</th>
                    <th>Subtotal (R$)</th>
                </tr>
            </thead>
            <tbody>"""

    for count, group_title, spec, subtotal in usage_data:
        html_template += f"""
                <tr>
                    <td class="col-qtd">{count}</td>
                    <td><strong>{group_title} (ID: {spec.id})</strong></td>
                    <td>{spec.length} x {spec.width} mm</td>
                    <td>R$ {format_brl(spec.price)}</td>
                    <td style="font-weight: 500;">R$ {format_brl(subtotal)}</td>
                </tr>"""

    html_template += f"""
                <tr>
                    <td colspan="4" style="text-align: right; font-weight: bold; padding-top: 15px;">Custo Total Estimado:</td>
                    <td style="font-weight: 700; color: var(--terra); font-size: 15px; padding-top: 15px;">R$ {format_brl(grand_total)}</td>
                </tr>
            </tbody>
        </table>
        <div class="page-break"></div>
"""

    for group_title, boards in results.items():
        html_template += f'<h2 class="section-title">Cortes - {group_title}</h2>\n'
        for i, board in enumerate(boards):
            spec = board.board_spec
            html_template += f"""
            <div class="board-container">
                <div class="board-header">Chapa {i+1} de {len(boards)} | <strong>ID {spec.id}</strong> ({spec.length} x {spec.width} mm)</div>
                <svg viewBox="0 0 {spec.length} {spec.width}" style="width: 100%; border: 2px solid var(--navy); background-color: #E5DFD5;">
            """
            for p in board.placed_parts:
                html_template += f'<rect x="{p.x}" y="{p.y}" width="{p.w}" height="{p.h}" fill="var(--sand)" stroke="var(--wood)" stroke-width="3" />\n'
                cx = p.x + (p.w / 2)
                cy = p.y + (p.h / 2)
                font_size_func = min(p.w * 0.08, p.h * 0.25, 45)
                font_size_dim = min(p.w * 0.06, p.h * 0.20, 35)

                html_template += f"""
                <text x="{cx}" y="{cy - (font_size_func*0.3)}" font-size="{font_size_func}" fill="var(--navy)" text-anchor="middle" dominant-baseline="middle" font-weight="700">{p.function}</text>
                <text x="{cx}" y="{cy + (font_size_dim*1.2)}" font-size="{font_size_dim}" fill="var(--terra)" text-anchor="middle" dominant-baseline="middle">{p.w} x {p.h}</text>
                """
            html_template += """
                </svg>
            </div>
            """

    html_template += f"""
        <footer>
            <p>{footer_html}</p>
        </footer>
    </div>
</body>
</html>"""

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
    except IOError as e:
        sys.exit(f"\n[ERRO CRÍTICO] Falha ao salvar o relatório HTML:\n{str(e)}")


def print_help_menu():
    """Displays comprehensive guidance on CSV schema formatting, optimization modes, and execution depth."""
    print("\n" + "="*78)
    print("      AJUDA E INSTRUÇÕES DE USO - GUIA COMPLETO DO SISTEMA DE CORTE")
    print("="*78)
    
    print("\n[ 1. GUIA DE SELEÇÃO DE MODO DE OTIMIZAÇÃO ]")
    print("  • (D) Otimização Dupla [Recomendado]:")
    print("      Prioriza em 1º lugar o MENOR CUSTO TOTAL (R$). Se houver empate entre")
    print("      combinações com o mesmo custo, escolhe a que tiver o MENOR DESPERDÍCIO")
    print("      GEOMÉTRICO (m²). É a melhor opção para a maioria dos projetos.")
    print("  • (G) Otimização Geométrica:")
    print("      Ignora o preço das chapas e foca 100% em minimizar o espaço sobressalente")
    print("      e o número total de chapas. Ideal quando todas as chapas têm o mesmo")
    print("      preço por m² ou quando o objetivo é minimizar o desperdício físico.")
    print("  • (F) Otimização Financeira:")
    print("      Foca estritamente em gastar o menor valor absoluto em R$ na loja, mesmo")
    print("      que isso resulte em retalhos geométricos maiores no relatório final.")

    print("\n[ 2. GUIA DE PROFUNDIDADE DO CÁLCULO (ITERAÇÕES) ]")
    print("  • (1) Rápido (100 iterações ~0,1 seg):")
    print("      Ideal para testes prévios rápidos durante a fase inicial do projeto.")
    print("  • (2) Padrão (2.000 iterações ~1,0 seg) [Recomendado]:")
    print("      Equilíbrio perfeito entre velocidade e busca avançada para projetos comuns")
    print("      (até 50 peças). Encontra excelentes encaixes quase instantaneamente.")
    print("  • (3) Profundo (10.000 iterações ~3,0 seg):")
    print("      Recomendado para projetos grandes (50+ peças) ou com muitas opções de")
    print("      chapas brutas diferentes. Permite explorar milhares de permutações a fundo.")

    print("\n[ 3. FORMATO DOS ARQUIVOS CSV DE ENTRADA ]")
    print("  DICA: Os cabeçalhos abaixo devem existir na Linha 1 (em qualquer ordem).\n")
    
    print("  ARQUIVO A: MATÉRIAS-PRIMAS (Chapas Brutas)")
    print("    - id             : ID único da chapa (ex: 1, 2, CHAPA-A)")
    print("    - Comprimento    : Medida em mm (ex: 2750)")
    print("    - Largura        : Medida em mm (ex: 1830)")
    print("    - Profundidade   : Espessura em mm (ex: 15)")
    print("    - Materia_prima  : Nome descritivo (ex: MDF Branco)")
    print("    - custo_unidade  : Preço unitário da chapa (ex: 150.00 ou 150,00)")
    print("    - Largura_corte  : Espessura da serra/kerf em mm (Opcional, Padrão: 3)")
    print("    - Qtd            : Limite de estoque físico (Opcional, Padrão: Infinito)")
    
    print("\n  ARQUIVO B: LISTA DE CORTE (Peças do Projeto)")
    print("    - Quantidade     : Quantidade de peças iguais (ex: 4)")
    print("    - Comprimento    : Medida em mm (ex: 780)")
    print("    - Largura        : Medida em mm (ex: 100)")
    print("    - Profundidade   : Espessura em mm (ex: 15)")
    print("    - Função         : Descrição/Nome da peça (ex: Lateral Gaveta)")
    print("    - Material       : IDs das chapas onde pode ser cortada (ex: 1,3)")
    print("    - Girar          : 'Sim' ou 'Não' (Permite rotação de 90º)")
    print("\n    [OPCIONAL - RECURSOS EXTRAS]")
    print("    - Comentários       : Linhas que começam com '//' serão ignoradas pelo sistema.")
    print("    - Espessura da Fita : Desconta bordas em mm (ex: 1)")
    print("    - Fita_C1, Fita_C2  : Marque 'x' para descontar fita nos Comprimentos")
    print("    - Fita_L1, Fita_L2  : Marque 'x' para descontar fita nas Larguras")
    print("="*78)
    input("\nPressione [ENTER] para retornar ao menu principal...")


def get_user_contact_info() -> UserContactInfo:
    """Prompts the user to enter their contact details for the HTML report header and footer."""
    print("\n" + "-"*60)
    print(" INFORMAR DADOS DE CONTATO PARA O RELATÓRIO HTML (OPCIONAL)")
    print(" (Pressione ENTER em qualquer campo para deixar em branco)")
    print("-" * 60)
    
    name = input("Nome do Responsável / Marceneiro: ").strip()
    phone = input("Telefone / WhatsApp: ").strip()
    email = input("E-mail: ").strip()
    
    return UserContactInfo(name=name, phone=phone, email=email)


def main():
    """Main CLI entry point managing input validation, user settings, and execution pipeline."""
    if len(sys.argv) > 2:
        cut_list_file = sys.argv[1].strip('"').strip("'")
        raw_wood_file = sys.argv[2].strip('"').strip("'")
    else:
        cut_list_file = input("Digite o caminho do CSV da Lista de Corte (ou 'Q' para Sair): ").strip('"').strip("'")
        if cut_list_file.upper() in ['Q', 'SAIR']:
            sys.exit("\nPrograma encerrado pelo usuário. Até logo!")

        raw_wood_file = input("Digite o caminho do CSV de Matérias-Primas (ou 'Q' para Sair): ").strip('"').strip("'")
        if raw_wood_file.upper() in ['Q', 'SAIR']:
            sys.exit("\nPrograma encerrado pelo usuário. Até logo!")

    cut_list_path = Path(cut_list_file).resolve()
    raw_wood_path = Path(raw_wood_file).resolve()

    if not cut_list_path.exists(): 
        sys.exit(f"\n[ERRO] Arquivo de lista de corte não encontrado: {cut_list_path}")
    if not raw_wood_path.exists(): 
        sys.exit(f"\n[ERRO] Arquivo de matérias-primas não encontrado: {raw_wood_path}")

    # Prompt user for contact details to include in the HTML report
    user_info = get_user_contact_info()

    # Optimization Mode Selection Loop
    while True:
        print("\nEscolha o Modo de Otimização (ou 'H' para Ajuda, 'Q' para Sair):")
        print("D) Otimização Dupla (Geométrica e Financeira) [PADRÃO]")
        print("G) Otimização Geométrica (Priorizar aproveitamento de área)")
        print("F) Otimização Financeira (Priorizar custo mais baixo)")
        print("H) Menu de Ajuda e Instruções do Sistema")
        print("Q) Sair do Programa")
        
        opt_mode = input("Opção [D, G, F, H ou Q]: ").strip().upper()
        if not opt_mode: 
            opt_mode = 'D'

        if opt_mode in ['Q', 'SAIR']:
            sys.exit("\nPrograma encerrado pelo usuário. Até logo!")
        elif opt_mode == 'H':
            print_help_menu()
        elif opt_mode in ['D', 'G', 'F']:
            break
            
    mode_names = {
        'D': 'Dupla (Custo e Geometria)',
        'G': 'Geométrica (Menor Desperdício)',
        'F': 'Financeira (Menor Custo)'
    }

    # Processing Depth (Iterations) Selection Loop
    while True:
        print("\nEscolha o nível de profundidade do cálculo (ou 'Q' para Sair):")
        print("1) Rápido (100 iterações ~0.1 seg)")
        print("2) Padrão (2.000 iterações ~1.0 seg) [PADRÃO]")
        print("3) Profundo (10.000 iterações ~3.0 seg)")
        print("Q) Sair do Programa")
        
        choice = input("Opção [1, 2, 3 ou Q]: ").strip().upper()
        if not choice: 
            choice = '2'

        if choice in ['Q', 'SAIR']:
            sys.exit("\nPrograma encerrado pelo usuário. Até logo!")

        iter_map = {"1": 100, "2": 2000, "3": 10000}
        if choice in iter_map:
            iterations = iter_map[choice]
            break

    print(f"\nValidando arquivos e otimizando corte ({mode_names[opt_mode]}) com {iterations:,} iterações...")

    output_path = cut_list_path.parent / f"{cut_list_path.stem}_plano_de_corte.html"

    # Load and validate CSVs
    raw_materials = read_raw_materials_csv(raw_wood_path)
    cut_list = read_cut_list_csv(cut_list_path)
    
    # Run Monte Carlo Bin-Packing optimization engine
    optimized_layouts = optimize_cuts(cut_list, raw_materials, iterations, opt_mode)
    
    # Render final HTML output with personalized contact info
    generate_html_report(optimized_layouts, output_path, mode_names[opt_mode], iterations, user_info)

    # Inform the user of the output location upon completion
    print("\n" + "="*78)
    print("   [SUCESSO] OTIMIZAÇÃO CONCLUÍDA COM SUCESSO!")
    print("   O relatório visual em HTML foi salvo em:")
    print(f"   -> {output_path}")
    print("="*78 + "\n")


if __name__ == "__main__":
    main()
