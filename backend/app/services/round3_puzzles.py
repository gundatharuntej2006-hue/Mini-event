"""Server-side puzzle bank for the automated Round 3 stations.

Answers never leave this module.  The browser receives only the public puzzle
payload and the API compares a normalized submission on the server.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Puzzle:
    key: str
    title: str
    eyebrow: str
    story: str
    prompt: str
    display: tuple[str, ...]
    answers: tuple[str, ...]
    answer_label: str
    visual_kind: str = "cards"


def normalize_answer(value: str) -> str:
    """Forgiving comparison: ignore case, spaces and punctuation."""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


_BASE_PUZZLES: dict[int, tuple[Puzzle, ...]] = {
    1: (
        Puzzle("1A", "The Chai Alibi", "LOGIC / CANTEEN CHAOS", "Four suspects ordered chai. Only one statement can be true.", "Who spilled the principal's tea?", ("Asha: ‘Bala did it.’", "Bala: ‘Charan did it.’", "Charan: ‘Bala is lying.’", "Divya: ‘I did not do it.’"), ("divya",), "Enter the name"),
        Puzzle("1B", "Auto-Rickshaw Alibi", "LOGIC / TRAFFIC FILE", "Exactly one driver is telling the truth.", "Which auto has the missing envelope?", ("Auto 1: ‘It is in Auto 2.’", "Auto 2: ‘It is not here.’", "Auto 3: ‘It is not in Auto 1.’"), ("auto1", "1", "autoone"), "Auto number"),
        Puzzle("1C", "The Samosa Switch", "LOGIC / SNACK INTELLIGENCE", "One box has only spicy samosas, one only sweet, and one mixed. Every label is wrong.", "You pick one sweet samosa from the box labelled MIXED. What is that box really?", ("SPICY", "SWEET", "MIXED"), ("sweet", "sweetonly"), "Box contents"),
        Puzzle("1D", "Hostel Room 404", "LOGIC / ROOM SEARCH", "The key is in exactly one room. The warden confirms that only notes 101 and 202 are truthful.", "Where is the key?", ("101: The key is not in 202.", "202: The key is in 303.", "303: The key is not here.", "404: The key is in 101."), ("303", "room303"), "Room number"),
    ),
    2: (
        Puzzle("2A", "Emoji Contraband", "PATTERN / VISUAL CODE", "The customs scanner reads the English initial of each emoji.", "Decode the final cargo word.", ("🌙 MOON  ·  🍦 ICE CREAM  ·  🐀 RAT", "🐀 RAT  ·  🍊 ORANGE  ·  📻 RADIO", "Read their initials."), ("mirror",), "Decoded word"),
        Puzzle("2B", "Cinema Seat Cipher", "PATTERN / NIGHT SHOW", "The booking clerk uses the same hidden step each time.", "What comes next?", ("A1 → C2", "C2 → F4", "F4 → J7", "J7 → ?"), ("o11",), "Seat code"),
        Puzzle("2C", "Filter Coffee Code", "PATTERN / CAFE SIGNAL", "Each cup shows the number of letters after removing repeated letters.", "What number belongs to FILTER COFFEE?", ("CHAI → 4", "COCOA → 3", "BANANA → 3", "FILTERCOFFEE → ?"), ("8", "eight"), "Number"),
        Puzzle("2D", "Metro Platform", "PATTERN / TRANSIT", "The display is running a mischievous number sequence.", "Which platform flashes next?", ("2, 6, 12, 20, 30, ?", "The gaps are the clue."), ("42", "fortytwo"), "Platform number"),
    ),
    3: (
        Puzzle("3A", "The Missing Meme", "WORDPLAY / GROUP CHAT", "A club member deleted one word from a very suspicious message.", "Find the word that connects all three clues.", ("court ___", "phone ___", "upper ___"), ("case",), "Shared word"),
        Puzzle("3B", "Professor's Password", "WORDPLAY / FACULTY WIFI", "The professor loves words hiding across other words.", "Which animal is hiding in the sentence?", ("THE MUSIC ATRIUM IS CLOSED", "Ignore the space between words."), ("cat",), "Animal"),
        Puzzle("3C", "The Dramatic Typo", "WORDPLAY / NOTICE BOARD", "Move one letter from the first word to the second to make two new valid words.", "Turn STEAL + POT into two new words.", ("STEAL  +  POT", "Move exactly one letter."), ("seat plot", "seatplot"), "Two new words"),
        Puzzle("3D", "Bollywood Alias", "WORDPLAY / CAST LIST", "Read the first letter of each line.", "What alias is hidden?", ("Silent in the corridor", "Every camera went dark", "Curiously, the gate opened", "Rumours filled the room", "Everyone blamed the guard", "Truth waited outside"), ("secret",), "Hidden alias"),
    ),
    4: (
        Puzzle("4A", "Lift to Nowhere", "SPATIAL / CAMPUS TOWER", "The lift starts on floor 4: up 3, down 5, up 7, down 2.", "Which floor opens?", ("START 04", "+3  −5  +7  −2"), ("7", "seven", "floor7"), "Floor"),
        Puzzle("4B", "Canteen Compass", "SPATIAL / DELIVERY RUN", "Face north. Turn right, walk 3; turn left, walk 2; turn left, walk 3.", "Which direction are you facing?", ("N ↑", "R +3  ·  L +2  ·  L +3"), ("west", "w"), "Direction"),
        Puzzle("4C", "The Crooked Map", "SPATIAL / TREASURE TRACE", "A runner goes 4 east, 3 north, 4 west and 1 south.", "How far and in which direction from the start?", ("→4  ↑3  ←4  ↓1",), ("2north", "north2", "twonorth"), "Distance + direction"),
        Puzzle("4D", "Mirror Clock", "SPATIAL / TIME GLITCH", "An analogue clock seen in a mirror appears to show 03:20.", "What is the actual time?", ("MIRROR DISPLAY  03:20", "Use 11:60 − mirror time."), ("840", "0840", "8:40"), "Actual time"),
    ),
    5: (
        Puzzle("5A", "The Fake UPI Receipt", "DEDUCTION / PAYMENT DESK", "Three receipts use a rule: the last digit equals the sum of the first three digits, keeping only the final digit.", "Which receipt is fake?", ("2417", "3520", "6119", "4307"), ("6119",), "Receipt number"),
        Puzzle("5B", "Library Fine", "DEDUCTION / OVERDUE FILE", "The fine doubles every late day. On day 6 it is ₹64.", "What was the fine on day 1?", ("DAY 6  ₹64", "Each earlier day is half."), ("2", "rs2", "₹2", "tworupees"), "Day-one fine"),
        Puzzle("5C", "The Suspicious Bill", "DEDUCTION / CANTEEN AUDIT", "Three dosas and two coffees cost ₹190. One dosa and two coffees cost ₹90.", "What does one dosa cost?", ("3D + 2C = 190", "1D + 2C = 90"), ("50", "rs50", "₹50"), "Dosa price"),
        Puzzle("5D", "Attendance Heist", "DEDUCTION / CLASS REGISTER", "A class is 60% present. Six late students enter and attendance becomes 75%.", "How many students are in the class?", ("BEFORE 60%", "+6 STUDENTS", "AFTER 75%"), ("40", "forty"), "Class strength"),
    ),
    6: (
        Puzzle("6A", "The Odd CCTV", "OBSERVATION / CAMERA WALL", "One timestamp breaks the camera's repeating rule.", "Which timestamp is corrupted?", ("12:21", "13:31", "14:41", "15:52", "16:61"), ("1552", "15:52"), "Timestamp"),
        Puzzle("6B", "Clone ID", "OBSERVATION / ACCESS LOG", "Seven IDs look similar. One is not a rotation of the others.", "Which ID is the intruder?", ("M69W", "W96M", "M96W", "W69M"), ("m96w",), "Intruder ID"),
        Puzzle("6C", "The Quiet Witness", "OBSERVATION / INTERVIEW", "Count only the words containing two consecutive identical letters.", "How many suspicious words are present?", ("The sleepy bookkeeper offered coffee in the committee room.",), ("5", "five"), "Count"),
        Puzzle("6D", "Licence Plate Blur", "OBSERVATION / PARKING", "One plate contains digits that do not remain valid when the display rotates 180°.", "Which plate fails?", ("808", "609", "347", "986", "619"), ("347",), "Plate"),
    ),
    7: (
        Puzzle("7A", "Voice Note Disaster", "SEQUENCE / AUDIO LOG", "A 4-beat ringtone repeats. The 19th beat triggered the alarm.", "Which sound played?", ("1 CLAP", "2 SNAP", "3 BELL", "4 BOOP", "repeat…"), ("bell",), "Sound"),
        Puzzle("7B", "Parcel Conveyor", "SEQUENCE / WAREHOUSE", "Boxes repeat RED, BLUE, BLUE, GOLD.", "What colour is box 31?", ("R · B · B · G · R · B · B · G …",), ("blue",), "Colour"),
        Puzzle("7C", "Unlucky Locker", "SEQUENCE / LOCKER BAY", "Locker numbers follow 1, 2, 6, 24, 120…", "What are the last two digits of the next locker number?", ("01  02  06  24  120  ?",), ("20", "twenty"), "Last two digits"),
        Puzzle("7D", "Dance Floor Signal", "SEQUENCE / DJ BOOTH", "The lights pulse 1, 1, 2, 3, 5, 8…", "How many pulses in the next burst?", ("●  ●  ●●  ●●●  ●●●●●  ●●●●●●●●",), ("13", "thirteen"), "Pulse count"),
    ),
    8: (
        Puzzle("8A", "The Great Biryani Split", "QUICK THINK / DINNER", "Five friends split two identical biryanis equally. Each biryani has 10 pieces.", "How many pieces per friend?", ("🍲 × 2", "20 PIECES / 5 FRIENDS"), ("4", "four"), "Pieces"),
        Puzzle("8B", "Security Guard's Age", "QUICK THINK / GATE LOG", "Five years ago Ravi was twice Mina's age. Ravi is 25 now.", "How old is Mina now?", ("RAVI NOW 25", "5 YEARS AGO: RAVI = 2 × MINA"), ("15", "fifteen"), "Age"),
        Puzzle("8C", "The Vanishing Rupee", "QUICK THINK / CASH BOX", "A ₹100 note is changed into exactly 10 notes using only ₹10 and ₹20 notes.", "How many ₹20 notes are there?", ("TOTAL ₹100", "10 NOTES", "₹10 + ₹20 only"), ("0", "zero", "none"), "Number of ₹20 notes"),
        Puzzle("8D", "Midnight Code", "QUICK THINK / FINAL LOCK", "The code is the number of months with exactly 28 days.", "Enter the code.", ("JAN  FEB  MAR  APR  MAY  JUN", "JUL  AUG  SEP  OCT  NOV  DEC"), ("12", "twelve"), "Code"),
    ),
}


_VISUAL_KINDS = {
    1: "logic",
    2: "pattern",
    3: "word",
    4: "spatial",
    5: "deduction",
    6: "observation",
    7: "sequence",
    8: "quick",
}

_NAMES = (
    "Aarav", "Bhavya", "Charan", "Divya", "Eshan", "Farah", "Girish", "Harini",
    "Ishaan", "Jhanvi", "Karthik", "Lavanya", "Manav", "Nandini", "Omkar", "Pooja",
    "Qadir", "Ritika", "Sanjay", "Tanvi", "Uday", "Varsha", "Wasim", "Yamini",
)


def _puzzle(table: int, index: int, title: str, eyebrow: str, story: str, prompt: str,
            display: tuple[str, ...], answers: tuple[str, ...], answer_label: str) -> Puzzle:
    return Puzzle(
        key=f"{table}G{index:02d}", title=title, eyebrow=eyebrow, story=story,
        prompt=prompt, display=display, answers=answers, answer_label=answer_label,
        visual_kind=_VISUAL_KINDS[table],
    )


def _logic_puzzles(count: int) -> tuple[Puzzle, ...]:
    items: list[Puzzle] = []
    objects = (("jalebi", "spicy", "sweet"), ("badge", "orange", "pink"), ("file", "sealed", "open"))
    for i in range(count):
        a, b, c, d = (_NAMES[(i * 4 + step) % len(_NAMES)] for step in range(4))
        number = i + 1
        mode = i % 3
        if mode == 0:
            items.append(_puzzle(1, number, f"Canteen Alibi #{number}", "LOGIC / ONE TRUE VOICE",
                "Four club members give statements. Exactly one statement is true.", "Who hid the event pass?",
                (f"{a}: ‘{b} hid it.’", f"{b}: ‘{c} hid it.’", f"{c}: ‘{b} is lying.’", f"{d}: ‘I did not hide it.’"),
                (d,), "Enter the name"))
        elif mode == 1:
            items.append(_puzzle(1, number, f"The Chai Queue #{number}", "LOGIC / QUEUE CAMERA",
                "Four people stood in one line. The camera recovered three reliable clues.", "Who was second in line?",
                (f"{a} stood before {b}.", f"{c} stood immediately after {b}.", f"{d} stood before {a}.", "No positions were shared."),
                (a,), "Second person"))
        else:
            thing, first, second = objects[i % len(objects)]
            items.append(_puzzle(1, number, f"The Wrong Labels #{number}", "LOGIC / BOX SWITCH",
                f"Three boxes contain only {first} {thing}s, only {second} {thing}s, or a mixture. Every label is wrong.",
                f"One {first} {thing} is drawn from the box labelled MIXED. What does that box actually contain?",
                (f"{first.upper()} ONLY", f"{second.upper()} ONLY", "MIXED", "Every printed label is wrong."),
                (f"{first} only", first), "Actual contents"))
    return tuple(items)


def _pattern_puzzles(count: int) -> tuple[Puzzle, ...]:
    words = ("BENGALURU", "BACKPACK", "NOTEBOOK", "HEADPHONE", "VOLUNTEER", "TREASURE", "CAMPUS", "SECURITY")
    signals = (("PEACH", "PINK", "BLACK"), ("CLAP", "SNAP", "BELL"), ("AUTO", "METRO", "WALK"), ("DOSA", "CHAI", "MAGGI"))
    items: list[Puzzle] = []
    for i in range(count):
        number, mode = i + 1, i % 4
        if mode == 0:
            offset = (i // 4) * 3
            seq = [n * (n + 1) + offset for n in range(1, 6)]
            answer = 6 * 7 + offset
            items.append(_puzzle(2, number, f"Platform Pulse #{number}", "PATTERN / NUMBER DISPLAY",
                "A broken platform board repeats one mathematical movement.", "Which number flashes next?",
                ("  →  ".join(map(str, seq)) + "  →  ?", "Look at how each gap changes."), (str(answer),), "Next number"))
        elif mode == 1:
            start = (i * 2) % 8 + 1
            letters = [start]
            for jump in (2, 3, 4):
                letters.append(letters[-1] + jump)
            answer_pos = letters[-1] + 5
            display = tuple(f"{chr(64 + pos)}{step + 1}" for step, pos in enumerate(letters))
            items.append(_puzzle(2, number, f"Cinema Seat Trail #{number}", "PATTERN / LETTER LADDER",
                "The letter jump grows by one each time; the number rises normally.", "Enter the next seat code.",
                display + ("letter jumps: +2, +3, +4, then +5",),
                (f"{chr(64 + answer_pos)}5",), "Seat code"))
        elif mode == 2:
            word = words[(i // 4) % len(words)]
            unique = len(set(word.casefold()))
            items.append(_puzzle(2, number, f"Sticker Scanner #{number}", "PATTERN / UNIQUE LETTERS",
                "The scanner deletes every repeated copy of a letter and keeps one of each.",
                f"How many different letters remain in {word}?", (word, "Count each different letter once."),
                (str(unique),), "Unique-letter count"))
        else:
            cycle = signals[(i // 4) % len(signals)]
            position = 17 + i
            answer = cycle[(position - 1) % len(cycle)]
            items.append(_puzzle(2, number, f"Looping Signal #{number}", "PATTERN / REPEATING LOOP",
                "The three-part signal repeats without changing.", f"What appears at position {position}?",
                ("  ·  ".join(cycle) + "  ·  REPEAT", f"TARGET POSITION: {position}"), (answer,), "Signal"))
    return tuple(items)


_WORD_CONNECTIONS = (
    ("court", "phone", "stair", "case"), ("rain", "brain", "thunder", "storm"),
    ("door", "bus", "full", "stop"), ("tea", "lunch", "coffee", "break"),
    ("day", "moon", "spot", "light"), ("key", "skate", "story", "board"),
    ("head", "mile", "corner", "stone"), ("foot", "basket", "base", "ball"),
    ("star", "sword", "jelly", "fish"), ("data", "over", "work", "flow"),
    ("under", "over", "back", "ground"), ("bed", "bath", "class", "room"),
    ("news", "wall", "sand", "paper"), ("pass", "key", "code", "word"),
    ("home", "net", "frame", "work"), ("look", "work", "hide", "out"),
)

_HIDDEN_WORDS = (
    ("THE MUSIC ATRIUM IS CLOSED", "cat"), ("THE OLD OGRE MASK IS MISSING", "dog"),
    ("THE SHOW LATE TONIGHT", "owl"), ("THE MEAN TICKET CLERK LEFT", "ant"),
    ("CHECK THE CAMERA TRIPOD", "rat"), ("THE ROOF OXFORD TILE", "fox"),
    ("OPEN THE TUBE ARCHIVE", "bear"), ("READ THE MAIL I ONCE SENT", "lion"),
    ("FOLLOW THE MAP AND A NOTE", "panda"), ("THE CAMERA VENDOR CALLED", "raven"),
    ("KEEP THE LEMON KEY SAFE", "monkey"), ("PARDON, KEY NUMBER FOUR", "donkey"),
    ("THE AUTHOR SEALED IT", "horse"), ("THE SPOT TERMINAL IS DARK", "otter"),
    ("CHECK THE PRIZE BRACKET", "zebra"),
)


def _word_puzzles(count: int) -> tuple[Puzzle, ...]:
    items: list[Puzzle] = []
    for i in range(count):
        number = i + 1
        if i < len(_WORD_CONNECTIONS):
            one, two, three, answer = _WORD_CONNECTIONS[i]
            items.append(_puzzle(3, number, f"Missing Group-Chat Word #{number}", "WORDPLAY / LINK WORD",
                "One word completes all three short phrases.", "What is the shared word?",
                (f"{one} ___", f"{two} ___", f"{three} ___"), (answer,), "Shared word"))
        else:
            phrase, answer = _HIDDEN_WORDS[(i - len(_WORD_CONNECTIONS)) % len(_HIDDEN_WORDS)]
            items.append(_puzzle(3, number, f"Hidden Mascot #{number}", "WORDPLAY / LETTER SEARCH",
                "An animal name is hiding across letters—and it may cross a space.", "Which animal is hidden?",
                (phrase, "Ignore spaces while searching."), (answer,), "Animal"))
    return tuple(items)


def _spatial_puzzles(count: int) -> tuple[Puzzle, ...]:
    directions = ("north", "east", "south", "west")
    arrows = {"north": "↑", "east": "→", "south": "↓", "west": "←"}
    items: list[Puzzle] = []
    for i in range(count):
        number, mode = i + 1, i % 3
        if mode == 0:
            east, north, west, south = 3 + i % 5, 2 + i % 4, 1 + i % 3, 1 + i % 2
            x, y = east - west, north - south
            if x and not y:
                answer = f"{abs(x)} {'east' if x > 0 else 'west'}"
            elif y and not x:
                answer = f"{abs(y)} {'north' if y > 0 else 'south'}"
            else:
                answer = f"{abs(x)} {'east' if x > 0 else 'west'} {abs(y)} {'north' if y > 0 else 'south'}"
            items.append(_puzzle(4, number, f"Campus Drone Route #{number}", "SPATIAL / MAP TRACE",
                "A delivery drone follows the route exactly.", "Where is it relative to the start?",
                (f"{arrows['east']}{east}   {arrows['north']}{north}   {arrows['west']}{west}   {arrows['south']}{south}", "Give distance and direction(s)."),
                (answer,), "Final displacement"))
        elif mode == 1:
            start_index = i % 4
            turns = ("right", "left", "right", "right") if i % 2 else ("left", "right", "left", "left")
            index = start_index
            for turn in turns:
                index = (index + (1 if turn == "right" else -1)) % 4
            answer = directions[index]
            items.append(_puzzle(4, number, f"Security Guard Spin #{number}", "SPATIAL / COMPASS",
                f"The guard starts facing {directions[start_index].upper()}.", "Which direction is the guard facing now?",
                (f"START {arrows[directions[start_index]]} {directions[start_index].upper()}", "  →  ".join(turn.upper() for turn in turns)),
                (answer, answer[0]), "Direction"))
        else:
            hour = (i % 11) + 1
            minute = ((i * 5) % 12) * 5
            actual_total = (11 * 60 + 60 - (hour * 60 + minute)) % (12 * 60)
            actual_hour = (actual_total // 60) or 12
            actual_minute = actual_total % 60
            shown = f"{hour:02d}:{minute:02d}"
            actual = f"{actual_hour:02d}:{actual_minute:02d}"
            items.append(_puzzle(4, number, f"Mirror Clock #{number}", "SPATIAL / REFLECTION",
                "An analogue clock is being viewed only through a mirror.", "What is the actual time?",
                (f"MIRROR SHOWS  {shown}", "Use 11:60 minus the mirror time."),
                (actual, actual.replace(":", "")), "Actual time"))
    return tuple(items)


def _deduction_puzzles(count: int) -> tuple[Puzzle, ...]:
    items: list[Puzzle] = []
    for i in range(count):
        number, mode = i + 1, i % 3
        if mode == 0:
            snack = 30 + (i % 6) * 5
            drink = 10 + (i % 4) * 5
            total_a, total_b = 3 * snack + 2 * drink, snack + 2 * drink
            items.append(_puzzle(5, number, f"Canteen Audit #{number}", "DEDUCTION / BILL CHECK",
                "Two receipts use the same snack and drink prices.", "What is the price of one snack?",
                (f"3 SNACKS + 2 DRINKS = ₹{total_a}", f"1 SNACK  + 2 DRINKS = ₹{total_b}"),
                (str(snack), f"₹{snack}", f"rs{snack}"), "Snack price"))
        elif mode == 1:
            total = 40 + (i % 5) * 20
            present_before = total * 60 // 100
            arrivals = total * 15 // 100
            items.append(_puzzle(5, number, f"Attendance Rescue #{number}", "DEDUCTION / REGISTER",
                "Late arrivals change the attendance from 60% to 75%.", "How many students are in the class?",
                (f"PRESENT FIRST: {present_before}", f"LATE ARRIVALS: +{arrivals}", "FINAL ATTENDANCE: 75%"),
                (str(total),), "Class strength"))
        else:
            average = 12 + i % 8
            values = [average - 3, average - 1, average + 1]
            missing = average * 4 - sum(values)
            items.append(_puzzle(5, number, f"Lost Scorecard #{number}", "DEDUCTION / AVERAGE",
                "Four quiz scores have the stated average, but one score is smudged.", "What is the missing score?",
                (f"SCORES: {values[0]}, {values[1]}, {values[2]}, ?", f"AVERAGE: {average}"),
                (str(missing),), "Missing score"))
    return tuple(items)


_DOUBLE_SENTENCES = (
    "The sleepy bookkeeper offered coffee in the committee room.",
    "A balloon drifted across the classroom while the keeper snoozed.",
    "The committee added coffee, toffee and a spoon to the trolley.",
    "The cool referee greeted the football team near the pool.",
    "A green parrot peered through the glass classroom door.",
)


def _double_word_count(sentence: str) -> int:
    words = re.findall(r"[a-z]+", sentence.casefold())
    return sum(any(left == right for left, right in zip(word, word[1:])) for word in words)


def _observation_puzzles(count: int) -> tuple[Puzzle, ...]:
    items: list[Puzzle] = []
    for i in range(count):
        number, mode = i + 1, i % 3
        if mode == 0:
            start = 10 + (i % 10)
            good = [f"{start + j}:{start + j:02d}" for j in range(4)]
            broken = f"{start + 4}:{start + 5:02d}"
            entries = good[:2] + [broken] + good[2:]
            items.append(_puzzle(6, number, f"CCTV Timestamp #{number}", "OBSERVATION / ODD FRAME",
                "Four timestamps repeat the same number on both sides. One does not.", "Which timestamp is corrupted?",
                tuple(entries), (broken, broken.replace(":", "")), "Corrupted timestamp"))
        elif mode == 1:
            sentence = _DOUBLE_SENTENCES[(i // 3) % len(_DOUBLE_SENTENCES)]
            answer = _double_word_count(sentence)
            items.append(_puzzle(6, number, f"Double-Letter Witness #{number}", "OBSERVATION / TEXT SCAN",
                "Count words that contain at least one pair of identical consecutive letters.", "How many words qualify?",
                (sentence, "A word counts once even if it has two pairs."), (str(answer),), "Count"))
        else:
            base = 1200 + i * 7
            codes = [str(base + offset) for offset in (0, 11, 22, 33)]
            odd = str(base + 47)
            entries = tuple(codes[:2] + [odd] + codes[2:])
            items.append(_puzzle(6, number, f"Parcel Code Glitch #{number}", "OBSERVATION / DIFFERENCE",
                "Four parcel codes rise by exactly 11. One replacement code breaks the chain.", "Which code is the intruder?",
                entries, (odd,), "Intruder code"))
    return tuple(items)


def _sequence_puzzles(count: int) -> tuple[Puzzle, ...]:
    cycles = (("CLAP", "SNAP", "BELL", "BOOP"), ("RED", "BLUE", "BLUE", "GOLD"),
              ("CHAI", "DOSA", "MAGGI", "IDLI"), ("NORTH", "EAST", "SOUTH", "WEST"))
    items: list[Puzzle] = []
    for i in range(count):
        number, mode = i + 1, i % 3
        if mode == 0:
            cycle = cycles[(i // 3) % len(cycles)]
            position = 23 + i
            answer = cycle[(position - 1) % 4]
            items.append(_puzzle(7, number, f"Repeating Broadcast #{number}", "SEQUENCE / LOOP",
                "A four-part broadcast loops continuously.", f"What plays at position {position}?",
                ("  ·  ".join(cycle), f"TARGET: {position}"), (answer,), "Signal"))
        elif mode == 1:
            start = 2 + i % 6
            step = 3 + i % 5
            values = [start + step * n for n in range(5)]
            items.append(_puzzle(7, number, f"Token Counter #{number}", "SEQUENCE / FIXED STEP",
                "The token counter advances by an unchanged amount.", "What number comes next?",
                ("  →  ".join(map(str, values)) + "  →  ?", f"Fixed jump: {step}"),
                (str(values[-1] + step),), "Next number"))
        else:
            first, second = 1 + i % 3, 2 + i % 4
            values = [first, second]
            for _ in range(4):
                values.append(values[-1] + values[-2])
            items.append(_puzzle(7, number, f"DJ Pulse Chain #{number}", "SEQUENCE / ADD PREVIOUS TWO",
                "Every pulse count is the sum of the previous two counts.", "How many pulses come next?",
                ("  ·  ".join(map(str, values)) + "  ·  ?",), (str(values[-1] + values[-2]),), "Next pulse count"))
    return tuple(items)


def _quick_puzzles(count: int) -> tuple[Puzzle, ...]:
    trick_bank = (
        ("How many months have at least 28 days?", "12"),
        ("You overtake the runner in second place. What place are you now?", "second"),
        ("A rooster lays an egg on a sloping roof. Which side does it roll down?", "roosters do not lay eggs"),
        ("How many birthdays does the average person have?", "1"),
        ("A farmer has 17 goats; all but 9 wander away. How many remain?", "9"),
        ("Which weighs more: 1 kg of iron or 1 kg of cotton?", "same"),
    )
    items: list[Puzzle] = []
    for i in range(count):
        number, mode = i + 1, i % 4
        if mode == 0:
            friends = 4 + i % 4
            pieces_each = 3 + i % 5
            total = friends * pieces_each
            items.append(_puzzle(8, number, f"Emergency Pizza Split #{number}", "QUICK THINK / FAIR SHARE",
                "Every friend receives exactly the same number of slices.", "How many slices does each friend get?",
                (f"{total} SLICES", f"{friends} FRIENDS", "NO LEFTOVERS"), (str(pieces_each),), "Slices each"))
        elif mode == 1:
            younger_then = 7 + i % 7
            years_ago = 4 + i % 4
            older_now = younger_then * 2 + years_ago
            answer = younger_then + years_ago
            items.append(_puzzle(8, number, f"Security Age Check #{number}", "QUICK THINK / AGE",
                f"{years_ago} years ago, Ravi was twice Mina's age. Ravi is {older_now} now.", "How old is Mina now?",
                (f"RAVI NOW: {older_now}", f"{years_ago} YEARS AGO: RAVI = 2 × MINA"), (str(answer),), "Mina's age"))
        elif mode == 2:
            twenties = 1 + (i % 8)
            tens = 10 - twenties
            total = twenties * 20 + tens * 10
            items.append(_puzzle(8, number, f"Cash Counter #{number}", "QUICK THINK / NOTES",
                "A cashier uses exactly 10 notes, all either ₹10 or ₹20.", "How many ₹20 notes were used?",
                (f"TOTAL: ₹{total}", "10 NOTES", "ONLY ₹10 AND ₹20"), (str(twenties),), "Number of ₹20 notes"))
        else:
            prompt, answer = trick_bank[(i // 4) % len(trick_bank)]
            items.append(_puzzle(8, number, f"Trapdoor Question #{number}", "QUICK THINK / WORD TRAP",
                "Read the wording carefully. Speed is useful; assumptions are not.", prompt,
                ("NO CALCULATOR NEEDED", "THE WORDING IS THE CLUE"), (answer,), "Final answer"))
    return tuple(items)


_GENERATORS = {
    1: _logic_puzzles,
    2: _pattern_puzzles,
    3: _word_puzzles,
    4: _spatial_puzzles,
    5: _deduction_puzzles,
    6: _observation_puzzles,
    7: _sequence_puzzles,
    8: _quick_puzzles,
}

# 35 puzzles at stations 1–3 and 34 at stations 4–8: exactly 275.
_TARGET_COUNTS = {1: 35, 2: 35, 3: 35, 4: 34, 5: 34, 6: 34, 7: 34, 8: 34}
PUZZLES: dict[int, tuple[Puzzle, ...]] = {
    table: _BASE_PUZZLES[table] + _GENERATORS[table](_TARGET_COUNTS[table] - len(_BASE_PUZZLES[table]))
    for table in range(1, 9)
}

assert sum(len(items) for items in PUZZLES.values()) == 275
assert len({puzzle.key for items in PUZZLES.values() for puzzle in items}) == 275

_PUZZLE_INDEX = {puzzle.key: puzzle for items in PUZZLES.values() for puzzle in items}


def puzzle_for(table_number: int, sequence: int) -> Puzzle:
    choices = PUZZLES.get(table_number)
    if not choices:
        raise KeyError(f"No puzzle bank configured for table {table_number}")
    if sequence < 0 or sequence >= len(choices):
        raise IndexError(f"Table {table_number} has no unused puzzle at sequence {sequence}.")
    return choices[sequence]


def puzzle_by_key(key: str) -> Puzzle:
    try:
        return _PUZZLE_INDEX[key]
    except KeyError as problem:
        raise KeyError(key) from problem


def public_payload(puzzle: Puzzle) -> dict:
    return {
        "key": puzzle.key,
        "title": puzzle.title,
        "eyebrow": puzzle.eyebrow,
        "story": puzzle.story,
        "prompt": puzzle.prompt,
        "display": list(puzzle.display),
        "answer_label": puzzle.answer_label,
        "visual_kind": puzzle.visual_kind if puzzle.visual_kind != "cards" else _VISUAL_KINDS[int(puzzle.key[0])],
    }


def is_correct(puzzle: Puzzle, answer: str) -> bool:
    submitted = normalize_answer(answer)
    return bool(submitted) and submitted in {normalize_answer(item) for item in puzzle.answers}
