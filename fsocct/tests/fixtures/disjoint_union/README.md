# Disconnected R10b union

The operands are the two valid, disjoint tools immediately before
`r10bTrayArms/g371/op` in the [frozen R10b source](../../../cases/r10b/r10b.fs).
Their volumes are 87,991.49270238579 and 14,542.236365251882 mm³.

The union retains both solids. After private geometry copying for optional
same-domain unification, OCCT 7.9's Common of an output and its coincident input
can return empty. It is therefore not a reliable way to recover body identity.
The regression requires the actual boolean/copy/unification face history to
preserve each disconnected body's name, creator and volume.
