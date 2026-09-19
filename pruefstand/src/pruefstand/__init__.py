"""pruefstand — pytest-Prüfstand für CAD-Teile gegen einen Maschinenkontext."""
from .assembly import MontageError, Step, load_assembly
from .body import Body, Parts, load_mesh, load_step
from .form import (AbsatzResult, FormSpec, Kante, KerbeResult, SplitterResult, TeilForm,
                   UnverrundetResult, absatz, find_form, kanten, kerbe, load_form, splitter,
                   unverrundet)
from .frame import Frame
from .interface import (AMBIGUOUS, MISSING, UNIQUE, Interface, InterfaceResult, Match,
                        interface_ok, interfaces_by_id, load_interfaces)
from .machine import Machine, Scene, State
from .primitives import (Tool, access, anker_mm2, coverage, gap, lochtabelle, overlap,
                         print_pose, protrusion, relevance, same_as, screw_chain, stability,
                         sweep)
from .primitives.access import AccessResult
from .primitives.sweep import SweepResult
from .primitives.print_pose import PrintPoseResult
from .primitives.relevance import RelevanceResult
from .primitives.screw_chain import ScrewChainResult
from .primitives.stability import StabilityResult
from .printing import DruckSpec, DruckSpecFehler, Lastabschnitt, Profil, Teilspec, lade_druck_spec
from .region import Region
from .relevanz import Erklaert, Relevanz, TeilRelevanz, find_relevanz, load_relevanz
from .results import (CoverageResult, GapResult, OverlapResult, ProtrusionResult,
                      SameAsResult, record)
from .screws import Screw, load_screws, screws_by_id
from .teile import Auflage, Teil, TeileSpec, TeileSpecFehler, find_teile, load_teile

__all__ = [
    'Machine', 'State', 'Scene', 'Body', 'Parts', 'Frame', 'Region',
    'kanten', 'Kante', 'absatz', 'kerbe', 'unverrundet', 'splitter',
    'AbsatzResult', 'KerbeResult', 'UnverrundetResult', 'SplitterResult',
    'FormSpec', 'TeilForm', 'load_form', 'find_form',
    'Teil', 'Auflage', 'TeileSpec', 'TeileSpecFehler', 'load_teile', 'find_teile',
    'load_step', 'load_mesh',
    'gap', 'overlap', 'coverage', 'protrusion', 'same_as', 'sweep', 'relevance',
    'access', 'Tool', 'screw_chain', 'lochtabelle', 'Screw', 'load_screws', 'screws_by_id',
    'load_assembly', 'Step', 'MontageError',
    'Interface', 'Match', 'InterfaceResult', 'interface_ok', 'load_interfaces',
    'interfaces_by_id', 'UNIQUE', 'AMBIGUOUS', 'MISSING',
    'print_pose', 'stability', 'anker_mm2',
    'Profil', 'Lastabschnitt', 'Teilspec', 'DruckSpec', 'lade_druck_spec', 'DruckSpecFehler',
    'GapResult', 'OverlapResult', 'CoverageResult', 'ProtrusionResult', 'SameAsResult',
    'AccessResult', 'ScrewChainResult', 'PrintPoseResult', 'StabilityResult', 'SweepResult',
    'RelevanceResult',
    'Relevanz', 'TeilRelevanz', 'Erklaert', 'load_relevanz', 'find_relevanz',
    'record',
]
__version__ = '0.1.0'
