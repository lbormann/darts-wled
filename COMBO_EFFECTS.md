# Combo Effects (-CMB)

## Übersicht

Mit dem `-CMB` Argument können spezielle WLED-Effekte definiert werden, die auf bestimmte **Wurf-Kombinationen** (fieldNames) reagieren. Die Combo-Effekte haben eine **höhere Priorität** als Score-Effekte (`-S`) und Score-Area-Effekte (`-A`), aber **niedrigere Priorität** als Busted (`-B`), Game-Won (`-G`) und Match-Won (`-M`).

## Argument-Syntax

```
-CMB "fields=effect" ["zusatz_effect"] ["fields=effect"] ...
```

### Regeln

- Jeder String **mit** `=` startet eine **neue Combo-Definition**
  - **Links** vom `=`: Komma-getrennte `fieldName`-Liste (die Wurf-Kombination)
  - **Rechts** vom `=`: Effekt-Definition (identisch zu allen anderen Effekt-Argumenten)
- Strings **ohne** `=` sind **zusätzliche Random-Choice-Effekte** für die vorherige Combo
- Die **Reihenfolge der Würfe ist egal** — die fieldNames werden intern sortiert verglichen
- **Duplikate** sind erlaubt (z.B. `t1,t1,t1` für dreimal Triple-1)

### FieldName-Format

Die fieldNames kommen direkt vom Data-Feeder:

| Prefix | Bedeutung | Beispiele |
|--------|-----------|-----------|
| `s`    | Single    | `s1`, `s20`, `s5` |
| `d`    | Double    | `d1`, `d20`, `d25` (Bull) |
| `t`    | Triple    | `t1`, `t20`, `t19` |

**Hinweis:** `s25` = Single Bull, `d25` = Double Bull (Bullseye)

## Beispiele

### Eine einzelne Combo

Wenn der Spieler Single-1, Single-20 und Single-5 wirft (egal in welcher Reihenfolge), wird Effekt 63 in Rot abgespielt:

```bat
-CMB "s1,s20,s5=63|red"
```

### Eine Combo mit Random-Choice (mehrere mögliche Effekte)

Bei Match wird zufällig einer der beiden Effekte gewählt:

```bat
-CMB "s1,s20,s5=63|red" "102|blue|s200"
```

### Mehrere Combos in einem Argument

```bat
-CMB "s1,s20,s5=63|red" "t1,t1,t1=102|blue" "d20,d20,d20=48|green"
```

### Combo mit Random-Choice UND weitere Combo

Der zweite String `"102|blue"` gehört als Random-Choice zur ersten Combo (kein `=`).
Der dritte String `"t1,t1,t1=48|green"` startet eine neue Combo (hat `=`):

```bat
-CMB "s1,s20,s5=63|red" "102|blue" "t1,t1,t1=48|green"
```

### Mit Preset

```bat
-CMB "s1,s20,s5=ps|5"
```

### Mit Multi-Device (Endpoint-Targeting)

Effekt nur auf Endpoint 0 (erster `-WEPS` Eintrag):

```bat
-CMB "s1,s20,s5=63|red|e:0"
```

Effekt nur auf Endpoint 1 (zweiter `-WEPS` Eintrag):

```bat
-CMB "t1,t1,t1=102|blue|e:1"
```

### Mit Custom Duration

```bat
-CMB "s1,s20,s5=63|red|d:5"
```

### Vollständiges Beispiel

```bat
python darts-wled.py ^
  -WEPS 192.168.1.144 192.168.1.141 ^
  -CON=192.168.1.142:8079 ^
  -IDE=solid|green ^
  -S26=solid|red1 ^
  -S180=ps|4 ^
  -CMB "s1,s20,s5=63|red" "s20,s20,s20=ps|4" "t20,t20,t20=102|blue|e:0"
```

In diesem Beispiel:
- `s1 + s20 + s5` (egal welche Reihenfolge) → Effekt 63 in Rot
- `s20 + s20 + s20` → Preset 4
- `t20 + t20 + t20` → Effekt 102 in Blau, nur auf Endpoint 0
- Score 26 von einer **anderen** Kombination (z.B. `s6 + s10 + s10`) → `-S26 solid|red1` (normale Score-Verarbeitung)

## Prioritäts-Reihenfolge

Bei einem `darts-thrown` Event wird in dieser Reihenfolge geprüft:

1. **Combo-Effekt** (`-CMB`) — wenn die geworfenen fieldNames einer definierten Combo entsprechen
2. **Score-Effekt** (`-S26`, etc.) — wenn ein spezifischer Score-Effekt definiert ist
3. **Score-Area-Effekt** (`-A1`, etc.) — wenn der Score in einen definierten Bereich fällt
4. Kein Effekt konfiguriert → Log-Ausgabe

**Nicht betroffen** von Combos (eigene Event-Types, höhere Priorität):
- Busted (`-B`)
- Game-Won (`-G`) / High-Finish (`-HF`)
- Match-Won (`-M`)

## DartScore-Effekte (-DS)

Die `-DS` Einzelwurf-Effekte (z.B. `-DS20`, `-DSBULL`) werden **unabhängig** von Combos bei jedem Einzelwurf (`dart1-thrown`, `dart2-thrown`, `dart3-thrown`) abgespielt. Combos ersetzen nur den **Gesamtscore-Effekt** bei `darts-thrown`.

## Tracking & Reset

Die Combo-Erkennung trackt die `fieldName`-Werte aus den `dart1/2/3-thrown` Events pro Spieler. Das Tracking wird in folgenden Situationen automatisch zurückgesetzt:

| Event | Reset-Verhalten |
|-------|-----------------|
| `darts-thrown` | Reset nach Combo-Check (egal ob Match oder nicht) |
| `darts-pulled` | Reset (wichtig wenn weniger als 3 Darts geworfen wurden) |
| `busted` | Reset |
| `game-won` | Reset |
| `match-won` | Reset |
| `game-started` | Reset **aller** Spieler |
| `match-started` | Reset **aller** Spieler |

## Unterstützte Spielmodi

Combo-Effekte funktionieren in allen Spielmodi die `darts-thrown` Events senden:

- X01
- Random Checkout
- ATC / RTW
- CountUp
- Shanghai
- Gotcha
- Bermuda
- Cricket

**Hinweis:** Bermuda sendet keine `dart1/2/3-thrown` Events für Einzelwürfe, daher kann das Combo-Tracking dort nicht funktionieren (keine fieldNames verfügbar). Combos werden in Bermuda trotzdem geprüft, matchen aber nur wenn der Data-Feeder die Einzelwurf-Events sendet.

## Technische Details

- Die Combo-Logik ist in der separaten Datei `combo_effects.py` implementiert
- Klasse `ComboEffectTracker` — verwaltet Tracking und Matching
- Funktion `parse_combo_effects_argument()` — parst das `-CMB` Argument
- Thread-sicher: Tracking ist pro `playerIndex` isoliert
- Debug-Ausgaben mit `-DEB=1` zeigen Tracking, Check und Match-Details
