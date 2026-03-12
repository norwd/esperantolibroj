#!/usr/bin/env python3
"""
rename_files.py - Rename Esperanto ebook files to use proper Unicode hat characters
instead of the x-notation-like apostrophe convention (c' → ĉ, s' → ŝ, etc.)
and fix other naming issues.
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Explicit rename mapping: old filename (without .md) → new filename (without .md)
RENAMES = {
    "C'eh'a kaj slovaka antologio, I - Cxehxa kaj slovaka antologio 1":
        "Ĉeĥa kaj slovaka antologio, I - Ĉeĥa kaj slovaka antologio 1",
    "C'eh'a kaj slovaka antologio, II - Cxehxa kaj slovaka antologio 2":
        "Ĉeĥa kaj slovaka antologio, II - Ĉeĥa kaj slovaka antologio 2",
    "C__murdo_moe_000orient_moe.wpd - Darold":
        "Murdo en la Orienta Ekspreso - Agatha Christie",
    "C'u li_ - Henri Vallienne":
        "Ĉu li? - Henri Vallienne",
    "Dianto de la tombo de poeto - August S'enoa":
        "Dianto de la tombo de poeto - August Ŝenoa",
    "Eo - Schwerin, P.E_ - Gaja leganto per Esperanto":
        "Eo - Schwerin, P.E. - Gaja leganto per Esperanto",
    "Eo - Zamenhof, L.L_ - Fundamenta Krestomatio":
        "Eo - Zamenhof, L.L. - Fundamenta Krestomatio",
    "Eposoj el Antikva Ugarito_ Baal kaj Anat - Donald Broadribb":
        "Eposoj el Antikva Ugarito: Baal kaj Anat - Donald Broadribb",
    "Foje ec' pensi estas g'uo - Vinko Os'lak":
        "Foje eĉ pensi estas ĝuo - Vinko Oslak",
    "Frau'lino Julie - August Strindberg":
        "Fraŭlino Julie - August Strindberg",
    "Ho ve, miaj s'uoj! - Georg Froschel":
        "Ho ve, miaj ŝuoj! - Georg Froschel",
    "Humoraj'oj - Petr Tomasovsky":
        "Humoraĵoj - Petr Tomasovsky",
    "Jakobo k.c_ - Hasse Z_":
        "Jakobo k.c. - Hasse Z.",
    "Juda sag'o - Sigvard Feldbaum, red_":
        "Juda saĝo - Sigvard Feldbaum, red.",
    "Kie brulas, g'entlemanoj_ - Charles Bukowski":
        "Kie brulas, ĝentlemanoj? - Charles Bukowski",
    "Kurioza okazaj'o - Carlo Goldoni":
        "Kurioza okazaĵo - Carlo Goldoni",
    "La blanka malsano - Karel C'apek":
        "La blanka malsano - Karel Ĉapek",
    "La blankc'evala rajdanto - Theodor Storm":
        "La blankĉevala rajdanto - Theodor Storm",
    "La brava soldato S'vejk, 3 - Jaroslav Has'ek":
        "La brava soldato Ŝvejk, 3 - Jaroslav Haŝek",
    "La brava soldato S'vejk, IV - Jaroslav Hasek":
        "La brava soldato Ŝvejk, IV - Jaroslav Haŝek",
    "La brava soldato S'vejk - Jaroslav Hasek":
        "La brava soldato Ŝvejk - Jaroslav Haŝek",
    "La brava soldato Svejk, 2 - Jaroslav Hasek":
        "La brava soldato Ŝvejk, 2 - Jaroslav Haŝek",
    "La deka logo - Ana Manero, red_":
        "La deka logo - Ana Manero, red.",
    "La gnomau'to - Upton Sinclair":
        "La gnomaŭto - Upton Sinclair",
    "La insulo de felic'uloj - August Strindberg":
        "La insulo de feliĉuloj - August Strindberg",
    "La konscienco riproc'as - August Strindberg":
        "La konscienco riproĉas - August Strindberg",
    "La mortula s'ipo - B. Traven":
        "La mortula ŝipo - B. Traven",
    "La neg'a blovado - Aleksandr Pus'kin":
        "La neĝa blovado - Aleksandr Puŝkin",
    "La pas'o senelirejen - Jean Codjo":
        "La paŝo senelirejen - Jean Codjo",
    "La reg'o de la Ora rivero - John Ruskin":
        "La reĝo de la Ora rivero - John Ruskin",
    "La tempomas'ino - H. G. Wells":
        "La tempomaŝino - H. G. Wells",
    "La volo de l'c'ielo - Artur Lundkvist":
        "La volo de l'ĉielo - Artur Lundkvist",
    "Libro de apokrifoj - Karel C'apek":
        "Libro de apokrifoj - Karel Ĉapek",
    "Libro de l'humoraj'o - Paul de Lengyel":
        "Libro de l'humoraĵo - Paul de Lengyel",
    "Malnovaj mitoj c'eh'aj - Alois Jirasek":
        "Malnovaj mitoj ĉeĥaj - Alois Jirasek",
    "Nau' fabeloj - Karel C'apek":
        "Naŭ fabeloj - Karel Ĉapek",
    "Orm la Rug'a - Frans G. Bengtsson":
        "Orm la Ruĝa - Frans G. Bengtsson",
    "Palmodimanc'o de c'evalkomercisto - Andras Suto":
        "Palmodimanĉo de ĉevalkomercisto - Andras Suto",
    "Pastaj'o - konsideroj kaj historio - Marco Picasso":
        "Pastaĵo - konsideroj kaj historio - Marco Picasso",
    "Perloj de l'Sag'o - Baha'u'llah":
        "Perloj de l'Saĝo - Baha'u'llah",
    "Pipi S'trumpolonga - Astrid Lindgren":
        "Pipi Ŝtrumpolonga - Astrid Lindgren",
    "Pizulo kaj Simplulo - Aleksandro S'arov":
        "Pizulo kaj Simplulo - Aleksandro Ŝarov",
    "Pro Is'tar - Heinrich A. Luyken":
        "Pro Iŝtar - Heinrich A. Luyken",
    "Prologo - Augeno Mih'alski":
        "Prologo - Augeno Miĥalski",
    "Quo vadis_ I - Henryk Sienkiewicz":
        "Quo vadis? I - Henryk Sienkiewicz",
    "Quo vadis_ II - Henryk Sienkiewicz":
        "Quo vadis? II - Henryk Sienkiewicz",
    "R. U. R_ - Karel Capek":
        "R. U. R. - Karel Ĉapek",
    "S'aknovelo - Stefan Zweig":
        "Ŝaknovelo - Stefan Zweig",
    "S'i humilig'as por venki - Oliver Goldsmith":
        "Ŝi humiliĝas por venki - Oliver Goldsmith",
    "Vojag'impresoj - Valdemar langlet":
        "Vojaĝimpresoj - Valdemar Langlet",
    "Vojag'o al Faremido - Frigyes Karinthy":
        "Vojaĝo al Faremido - Frigyes Karinthy",
}


def rename_file(old_base, new_base, ext, dry_run=False):
    old_path = os.path.join(SCRIPT_DIR, old_base + ext)
    new_path = os.path.join(SCRIPT_DIR, new_base + ext)
    if os.path.exists(old_path):
        if dry_run:
            print(f"  WOULD RENAME: {old_base + ext}")
            print(f"             → {new_base + ext}")
        else:
            os.rename(old_path, new_path)
            print(f"  RENAMED: {old_base + ext}")
            print(f"        → {new_base + ext}")
        return True
    return False


def main():
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("DRY RUN - no files will be changed\n")

    renamed = 0
    skipped = 0

    for old_base, new_base in sorted(RENAMES.items()):
        if old_base == new_base:
            continue

        did_rename = rename_file(old_base, new_base, '.md', dry_run)
        if did_rename:
            renamed += 1
            # Also rename .bak file if it exists
            rename_file(old_base, new_base, '.md.bak', dry_run)
        else:
            # Check if the target already exists (already renamed)
            target = os.path.join(SCRIPT_DIR, new_base + '.md')
            if os.path.exists(target):
                print(f"  ALREADY CORRECT: {new_base}.md")
            else:
                print(f"  NOT FOUND: {old_base}.md")
            skipped += 1

    print(f"\nDone: {renamed} renamed, {skipped} skipped.")


if __name__ == '__main__':
    main()
