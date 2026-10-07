import { Team, RoundInfo, RoundProgressionStep, DashboardStats, ActivityLogItem } from '../types';

/**
 * Official 32 Teams for BMSIT Multi-Round Event (ODDYSSEY Protocol).
 * Sourced directly from verified database registration records.
 * Exactly 32 teams, 160 participants (5 per team).
 */
export const MOCK_TEAMS: Team[] = [
  {
    "id": "team-1001",
    "teamNumber": 1,
    "name": "Titans",
    "leaderName": "Swaroop Patil",
    "membersCount": 5,
    "members": [
      {
        "id": "part-b29ff729",
        "name": "Swaroop Patil",
        "email": "swarooppatil494@gmail.com",
        "usn": "1TD24CS308",
        "phone": "82961 79005",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1001",
        "teamName": "Titans"
      },
      {
        "id": "part-256763c5",
        "name": "Sanika Patil",
        "email": "24ug1bycs991@bmsit.in",
        "usn": "1TD24CS246",
        "phone": "97416 44790",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1001",
        "teamName": "Titans"
      },
      {
        "id": "part-41fbd1fc",
        "name": "Shreeya Suvarna",
        "email": "24ug1bycs1019@bmsit.in",
        "usn": "1BY24CS270",
        "phone": "82175 68370",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1001",
        "teamName": "Titans"
      },
      {
        "id": "part-538d9774",
        "name": "Sumukh R",
        "email": "24ug1bycs974@bmsit.in",
        "usn": "1TD24CS299",
        "phone": "83106 85372",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1001",
        "teamName": "Titans"
      },
      {
        "id": "part-953eb0cb",
        "name": "Sneha Tapse",
        "email": "24ug1bycs976@bmsit.in",
        "usn": "1TD24CS280",
        "phone": "8147876821",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1001",
        "teamName": "Titans"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 1",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1002",
    "teamNumber": 2,
    "name": "Coded",
    "leaderName": "Nikhil",
    "membersCount": 5,
    "members": [
      {
        "id": "part-2fffe703",
        "name": "Nikhil",
        "email": "sainikhilmeda89@gmail.com",
        "usn": "1BY25AI135",
        "phone": "9866456719",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1002",
        "teamName": "Coded"
      },
      {
        "id": "part-0cdb11c0",
        "name": "G Avinash Reddy",
        "email": "gavinashreddy95@gmail.com",
        "usn": "1TD25027",
        "phone": "8074489870",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1002",
        "teamName": "Coded"
      },
      {
        "id": "part-1c727255",
        "name": "Rohit",
        "email": "gudagerohit222@gmail.com",
        "usn": "1BY25AI200",
        "phone": "91084 93598",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1002",
        "teamName": "Coded"
      },
      {
        "id": "part-edd7cd2c",
        "name": "Sanchita Divakar",
        "email": "sanchitadivakar29@gmail.com",
        "usn": "1BY25AI211",
        "phone": "7892321548",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1002",
        "teamName": "Coded"
      },
      {
        "id": "part-fe21d161",
        "name": "Jaswanth",
        "email": "25ug1byai374@bmsit.in",
        "usn": "1BY25AI143",
        "phone": "9902162329",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1002",
        "teamName": "Coded"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 2",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1003",
    "teamNumber": 3,
    "name": "The Litt Up Crew",
    "leaderName": "Hriday Prabhakar",
    "membersCount": 5,
    "members": [
      {
        "id": "part-ef235a69",
        "name": "Hriday Prabhakar",
        "email": "hrudayprabhakar@gmail.com",
        "usn": "26UG1BYCS0859-T",
        "phone": "7829992525",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1003",
        "teamName": "The Litt Up Crew"
      },
      {
        "id": "part-51cf1301",
        "name": "Harshith U",
        "email": "harshithu1101@gmail.com",
        "usn": "26UG1BYCS0130-T",
        "phone": "9731433313",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1003",
        "teamName": "The Litt Up Crew"
      },
      {
        "id": "part-681ffb59",
        "name": "Prakhar Kumar",
        "email": "prakhar8oct@gmail.com",
        "usn": "26UG1BYCS0258-T",
        "phone": "8867486861",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1003",
        "teamName": "The Litt Up Crew"
      },
      {
        "id": "part-c1d910ab",
        "name": "Thanveer",
        "email": "thanveerahmed330@gmail.com",
        "usn": "26UG1BYCS0880-T",
        "phone": "9187426852",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1003",
        "teamName": "The Litt Up Crew"
      },
      {
        "id": "part-fcbe5bdf",
        "name": "Jyotiraditya Chotia",
        "email": "jyotiradityachotia@gmail.com",
        "usn": "26UG1BYCS0956-T",
        "phone": "9509789912",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1003",
        "teamName": "The Litt Up Crew"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 3",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1004",
    "teamNumber": 4,
    "name": "K-R-A-P-S ALLIANCE",
    "leaderName": "Sahil Hussain",
    "membersCount": 5,
    "members": [
      {
        "id": "part-af37ad8c",
        "name": "Sahil Hussain",
        "email": "sahilhussain.5519@gmail.com",
        "usn": "26UG1BYCS0980-T",
        "phone": "7001447657",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1004",
        "teamName": "K-R-A-P-S ALLIANCE"
      },
      {
        "id": "part-3d7c780f",
        "name": "Khyati Agarwal",
        "email": "khyatiag890@gmail.com",
        "usn": "26UG1BYCS1032-T",
        "phone": "9523840717",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1004",
        "teamName": "K-R-A-P-S ALLIANCE"
      },
      {
        "id": "part-a2a78ab7",
        "name": "Raj Yadav",
        "email": "rajyadav01012064@gmail.com",
        "usn": "26UG1BYCS1102-T",
        "phone": "9334399722",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1004",
        "teamName": "K-R-A-P-S ALLIANCE"
      },
      {
        "id": "part-a83aba93",
        "name": "Ananya Gowda",
        "email": "praphimant9@gmail.com",
        "usn": "26UG1BYCS0034-T",
        "phone": "8296676179",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1004",
        "teamName": "K-R-A-P-S ALLIANCE"
      },
      {
        "id": "part-d6893e5e",
        "name": "Parth Khandelwal",
        "email": "khandelwalparth101@gmail.com",
        "usn": "26UG1BYCS1021-T",
        "phone": "7060998696",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1004",
        "teamName": "K-R-A-P-S ALLIANCE"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 4",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1005",
    "teamNumber": 5,
    "name": "Ace of Spades",
    "leaderName": "Shourya Singh",
    "membersCount": 5,
    "members": [
      {
        "id": "part-0417fda1",
        "name": "Shourya Singh",
        "email": "rajputsourya307@gmail.com",
        "usn": "26UG1BYCS0869-T",
        "phone": "9229721291",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1005",
        "teamName": "Ace of Spades"
      },
      {
        "id": "part-254c4b27",
        "name": "Mohammad Shahid TM",
        "email": "shahidtm.1809@gmail.com",
        "usn": "26UG1BYCS0634-T",
        "phone": "8310875785",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1005",
        "teamName": "Ace of Spades"
      },
      {
        "id": "part-3e852051",
        "name": "Harsh Kumar Gupta",
        "email": "kumarguptaharsh686@gmail.com",
        "usn": "26UG1BYCS0987-T",
        "phone": "7762072106",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1005",
        "teamName": "Ace of Spades"
      },
      {
        "id": "part-5101d4cd",
        "name": "Sumanth Hegde",
        "email": "sumanthlhegde23@gmail.com",
        "usn": "26UG1BYCS0688-T",
        "phone": "9035050052",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1005",
        "teamName": "Ace of Spades"
      },
      {
        "id": "part-9aec04bc",
        "name": "Ali Asgher Amin",
        "email": "aliasgharamin11@gmail.com",
        "usn": "26UG1BYCS1073-T",
        "phone": "9527886684",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1005",
        "teamName": "Ace of Spades"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 5",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1006",
    "teamNumber": 6,
    "name": "Circuit breakers",
    "leaderName": "Sai Pranav N R",
    "membersCount": 5,
    "members": [
      {
        "id": "part-0b3227db",
        "name": "Sai Pranav N R",
        "email": "saipranavnr@gmail.com",
        "usn": "26UG1BYEC064-T",
        "phone": "6364252225",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1006",
        "teamName": "Circuit breakers"
      },
      {
        "id": "part-0f424aa8",
        "name": "Srujan j ballal",
        "email": "srujanjballal@gmail.com",
        "usn": "26UG1BYEC101-T",
        "phone": "6363716451",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1006",
        "teamName": "Circuit breakers"
      },
      {
        "id": "part-559e2caf",
        "name": "Raghav Vasudev Revankar",
        "email": "raghavrevankar55@gmail.com",
        "usn": "26UG1BYEC079-T",
        "phone": "8951532994",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1006",
        "teamName": "Circuit breakers"
      },
      {
        "id": "part-edbb1988",
        "name": "M Srishanth",
        "email": "m.srishanth20@gmail.com",
        "usn": "26UG1BYEC120-T",
        "phone": "7892412519",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1006",
        "teamName": "Circuit breakers"
      },
      {
        "id": "part-fd8c086e",
        "name": "Amey Hegade",
        "email": "ameyhegade5@gmail.com",
        "usn": "26UG1BYEC099-T",
        "phone": "9482074795",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1006",
        "teamName": "Circuit breakers"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 6",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1007",
    "teamNumber": 7,
    "name": "ERROR 404",
    "leaderName": "Jash kapopara",
    "membersCount": 5,
    "members": [
      {
        "id": "part-37fb87b0",
        "name": "Jash kapopara",
        "email": "jashjkapopara@gmail.com",
        "usn": "26UG1BYCS0892-T",
        "phone": "9328899449",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1007",
        "teamName": "ERROR 404"
      },
      {
        "id": "part-37542962",
        "name": "Naman",
        "email": "namankaashyapbmsit@gmail.com",
        "usn": "26UG1BYCS0177-T",
        "phone": "8095357810",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1007",
        "teamName": "ERROR 404"
      },
      {
        "id": "part-756c16c8",
        "name": "Vineeth patil",
        "email": "vineethvpatil@gmail.com",
        "usn": "26UG1BYCS0753-T",
        "phone": "8951806080",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1007",
        "teamName": "ERROR 404"
      },
      {
        "id": "part-b1bde9aa",
        "name": "Namish Goyal",
        "email": "nammu2069@gmail.com",
        "usn": "26UG1BYCS0595-T",
        "phone": "8448323447",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1007",
        "teamName": "ERROR 404"
      },
      {
        "id": "part-cc18768b",
        "name": "Divyansh",
        "email": "divyanshkm27@gmail.com",
        "usn": "26UG1BYCS0066-T",
        "phone": "9136352533",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1007",
        "teamName": "ERROR 404"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 7",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1008",
    "teamNumber": 8,
    "name": "Apex Archers",
    "leaderName": "ARJUN D",
    "membersCount": 5,
    "members": [
      {
        "id": "part-e5771cf6",
        "name": "ARJUN D",
        "email": "arjunappu9191@gmail.com",
        "usn": "26UG1BYAI055-T",
        "phone": "8618942997",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1008",
        "teamName": "Apex Archers"
      },
      {
        "id": "part-545dd440",
        "name": "Darshan N",
        "email": "darshanroyal905@gmail.com",
        "usn": "26UG1BYAI236-T",
        "phone": "8147744055",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1008",
        "teamName": "Apex Archers"
      },
      {
        "id": "part-68d85df7",
        "name": "Sathvic B M",
        "email": "sathvic@gmail.com",
        "usn": "26UG1BYAI-198T",
        "phone": "9380712933",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1008",
        "teamName": "Apex Archers"
      },
      {
        "id": "part-93a00c3f",
        "name": "Samrudh HN",
        "email": "samrudh19gowda@gmail.com",
        "usn": "26UG1BYAI206-T",
        "phone": "8792740819",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1008",
        "teamName": "Apex Archers"
      },
      {
        "id": "part-e0ac4fb3",
        "name": "MURARI D",
        "email": "muraridasari28@gmail.com",
        "usn": "26UG1BYAI143-T",
        "phone": "9148394354",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1008",
        "teamName": "Apex Archers"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 8",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1009",
    "teamNumber": 9,
    "name": "Babu warriors",
    "leaderName": "N Poorna Kruthi",
    "membersCount": 5,
    "members": [
      {
        "id": "part-11615e5e",
        "name": "N Poorna Kruthi",
        "email": "poornakruthimes26@gmail.com",
        "usn": "26UG1BYEE051-T",
        "phone": "6362067189",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1009",
        "teamName": "Babu warriors"
      },
      {
        "id": "part-5139f284",
        "name": "SAI SRI HAAS NIMASHAKAVI",
        "email": "srihaas.988@gmail.com",
        "usn": "26UG1BYEC204-T",
        "phone": "9740585753",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1009",
        "teamName": "Babu warriors"
      },
      {
        "id": "part-642ecf1b",
        "name": "Vrinda Rajashekar",
        "email": "vrindarajashekar@gmail.com",
        "usn": "26UG1BYEE072-T",
        "phone": "8431214064",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1009",
        "teamName": "Babu warriors"
      },
      {
        "id": "part-709d214b",
        "name": "Pranav Sirigiri",
        "email": "pranavsirigiri9@gmail.com",
        "usn": "26UG1BYEE071-T",
        "phone": "81474 89030",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1009",
        "teamName": "Babu warriors"
      },
      {
        "id": "part-c8fa18ff",
        "name": "Pranathi Muralidharan",
        "email": "mpranathi09@gmail.com",
        "usn": "26UG1BYEE045-T",
        "phone": "9187983969",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1009",
        "teamName": "Babu warriors"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 9",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1010",
    "teamNumber": 10,
    "name": "AFA-Anything For Attendance",
    "leaderName": "Ayan Faiz",
    "membersCount": 5,
    "members": [
      {
        "id": "part-9adc7a14",
        "name": "Ayan Faiz",
        "email": "faizayan029@gmail.com",
        "usn": "26UG1BYEE070-T",
        "phone": "9204004790",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1010",
        "teamName": "AFA-Anything For Attendance"
      },
      {
        "id": "part-18db8120",
        "name": "Moksh Hitesh Chheda",
        "email": "insaneinsaan4@gmail.com",
        "usn": "26UG1BYEE057-T",
        "phone": "9480264665",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1010",
        "teamName": "AFA-Anything For Attendance"
      },
      {
        "id": "part-668a9dc0",
        "name": "Mohammed usaid",
        "email": "mdusaid04@gmail.com",
        "usn": "26UG1BYEE055-T",
        "phone": "8073400278",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1010",
        "teamName": "AFA-Anything For Attendance"
      },
      {
        "id": "part-e52726a2",
        "name": "Mohammed Asif",
        "email": "theeasiiif@gmail.com",
        "usn": "UG1BYEE016-T",
        "phone": "9353949727",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1010",
        "teamName": "AFA-Anything For Attendance"
      },
      {
        "id": "part-ee89e051",
        "name": "D ARUN",
        "email": "the.d.arch.2008@gmail.com",
        "usn": "26UG1BYEE053-T",
        "phone": "9036338479",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1010",
        "teamName": "AFA-Anything For Attendance"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 10",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1011",
    "teamNumber": 11,
    "name": "Braniacs",
    "leaderName": "Unnati",
    "membersCount": 5,
    "members": [
      {
        "id": "part-29fc98d1",
        "name": "Unnati",
        "email": "unnatiekbote7@gmail.com",
        "usn": "26UG1BYEC116-T",
        "phone": "6360161529",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1011",
        "teamName": "Braniacs"
      },
      {
        "id": "part-043da2b7",
        "name": "Harsha",
        "email": "harshaamarpatil@gmail.com",
        "usn": "26UG1BYEC175-T",
        "phone": "7738613644",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1011",
        "teamName": "Braniacs"
      },
      {
        "id": "part-30678fca",
        "name": "Hitaishi A Alva",
        "email": "alvahitaishi@gmail.com",
        "usn": "26UG1BYEC185-T",
        "phone": "9180190821",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1011",
        "teamName": "Braniacs"
      },
      {
        "id": "part-3e61715b",
        "name": "Aleena Biju",
        "email": "aleenabiju56004@gmail.com",
        "usn": "26UG1BYEC052-T",
        "phone": "8904761558",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1011",
        "teamName": "Braniacs"
      },
      {
        "id": "part-4d272789",
        "name": "Anvika",
        "email": "anvikasash18@gmail.com",
        "usn": "26UG1BYEC210-T",
        "phone": "7019801365",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1011",
        "teamName": "Braniacs"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 11",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1012",
    "teamNumber": 12,
    "name": "Aryabatthas",
    "leaderName": "Syed Zain",
    "membersCount": 5,
    "members": [
      {
        "id": "part-aa768b04",
        "name": "Syed Zain",
        "email": "syedzain29.2008@gmail.com",
        "usn": "26UG1BYAI225-T",
        "phone": "9141179217",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1012",
        "teamName": "Aryabatthas"
      },
      {
        "id": "part-1e83d232",
        "name": "Poonchezhian A",
        "email": "poonchezhianarul@gmail.com",
        "usn": "26UG1BYAI028-T",
        "phone": "7010312975",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1012",
        "teamName": "Aryabatthas"
      },
      {
        "id": "part-2f121251",
        "name": "Reuven Varghese",
        "email": "reuven.varghese@gmail.com",
        "usn": "26UG1BYAI339-T",
        "phone": "8310492152",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1012",
        "teamName": "Aryabatthas"
      },
      {
        "id": "part-49b63296",
        "name": "Devansh Kumar Sahu",
        "email": "devanshsahu04042008@gmail.com",
        "usn": "26UG1BYAI096-T",
        "phone": "9424319047",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1012",
        "teamName": "Aryabatthas"
      },
      {
        "id": "part-da8517e3",
        "name": "A Mithil",
        "email": "mithilaineni@gmail.com",
        "usn": "26UG1BYAI390-T",
        "phone": "7892000466",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1012",
        "teamName": "Aryabatthas"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 12",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1013",
    "teamNumber": 13,
    "name": "Kingsmen",
    "leaderName": "Tejas M S",
    "membersCount": 5,
    "members": [
      {
        "id": "part-927efdbb",
        "name": "Tejas M S",
        "email": "tejasms986@gmail.com",
        "usn": "36UG1BYB027-T",
        "phone": "9180443724",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1013",
        "teamName": "Kingsmen"
      },
      {
        "id": "part-16804fb6",
        "name": "Vihaan Jino",
        "email": "vihaan7js@gmail.com",
        "usn": "26UG1BYBS077-T",
        "phone": "9972613859",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1013",
        "teamName": "Kingsmen"
      },
      {
        "id": "part-32298727",
        "name": "Sachita Praveen",
        "email": "sachithpraveen996@gmail.com",
        "usn": "26UG1BYBS061-T",
        "phone": "7483886208",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1013",
        "teamName": "Kingsmen"
      },
      {
        "id": "part-8e67d952",
        "name": "Soorya",
        "email": "soorya204944n@gmail.com",
        "usn": "26UG1BYBS060-T",
        "phone": "8660931010",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1013",
        "teamName": "Kingsmen"
      },
      {
        "id": "part-b81e08b4",
        "name": "Shourya S Kadintar",
        "email": "shouryaskadintar@gmail.com",
        "usn": "36UG1BYB057-T",
        "phone": "6364747064",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1013",
        "teamName": "Kingsmen"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 13",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1014",
    "teamNumber": 14,
    "name": "The high fives",
    "leaderName": "Yogeshwar H R",
    "membersCount": 5,
    "members": [
      {
        "id": "part-0a4c22d5",
        "name": "Yogeshwar H R",
        "email": "yogeshhr66@gmail.com",
        "usn": "26UG1BYCS0667-T",
        "phone": "8861204506",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1014",
        "teamName": "The high fives"
      },
      {
        "id": "part-4dd5094e",
        "name": "Shivshankar",
        "email": "shiv.official.111@gmail.com",
        "usn": "26UG1BYCS0877-T",
        "phone": "9955999751",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1014",
        "teamName": "The high fives"
      },
      {
        "id": "part-632bd773",
        "name": "S Praveen",
        "email": "praveensaye2206@gmail.com",
        "usn": "26UG1BYCS0874-T",
        "phone": "7995667435",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1014",
        "teamName": "The high fives"
      },
      {
        "id": "part-7bfa7453",
        "name": "Narasimha Swamy H M",
        "email": "swamyhm598@gmail.com",
        "usn": "26UG1BYCS0961-T",
        "phone": "9353164644",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1014",
        "teamName": "The high fives"
      },
      {
        "id": "part-8576421b",
        "name": "Sinchana M patil",
        "email": "psinchana080@gmail.com",
        "usn": "26UG1BYCS0041-T",
        "phone": "9731123973",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1014",
        "teamName": "The high fives"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 14",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1015",
    "teamNumber": 15,
    "name": "Team Rocket",
    "leaderName": "Aryan Rai",
    "membersCount": 5,
    "members": [
      {
        "id": "part-3b7eeeb2",
        "name": "Aryan Rai",
        "email": "aryanrai1602@gmail.com",
        "usn": "26UG1BYAI299-T",
        "phone": "9279554492",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1015",
        "teamName": "Team Rocket"
      },
      {
        "id": "part-75083ed8",
        "name": "Pranshu Malik",
        "email": "pranshu4329@gmail.com",
        "usn": "26UG1BYAI335-T",
        "phone": "+91 79883 55202",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1015",
        "teamName": "Team Rocket"
      },
      {
        "id": "part-b839c41d",
        "name": "Rudransh Paliwal",
        "email": "rudranshapaliwal2007@gmail.com",
        "usn": "26UG1BYCS0963-T",
        "phone": "+91 94243 01910",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1015",
        "teamName": "Team Rocket"
      },
      {
        "id": "part-ee28bd30",
        "name": "Preet Anand Gupta",
        "email": "jisgupta@gmail.com",
        "usn": "26UG1BYCS1248-T",
        "phone": "+91 95468 43575",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1015",
        "teamName": "Team Rocket"
      },
      {
        "id": "part-f2cfdfe9",
        "name": "Manan Gupta",
        "email": "manengupta@gmail.com",
        "usn": "26UG1BYCS0889-T",
        "phone": "+91 96676 99035",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1015",
        "teamName": "Team Rocket"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 15",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1016",
    "teamNumber": 16,
    "name": "Avalahalli Ninjas",
    "leaderName": "Srushti Mishra",
    "membersCount": 5,
    "members": [
      {
        "id": "part-dc98cdc5",
        "name": "Srushti Mishra",
        "email": "srushtimishra25@gmail.com",
        "usn": "26UG1BYCS0655-T",
        "phone": "9113508187",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1016",
        "teamName": "Avalahalli Ninjas"
      },
      {
        "id": "part-10f519c1",
        "name": "J Benito Nathanael",
        "email": "benitobernice1947@gmail.com",
        "usn": "26UG1BYCS0399-T",
        "phone": "7019195891",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1016",
        "teamName": "Avalahalli Ninjas"
      },
      {
        "id": "part-2a40688b",
        "name": "Kushisree Suresh",
        "email": "kushi.s.2534@gmail.com",
        "usn": "26UG1BYCS0313-T",
        "phone": "9945033174",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1016",
        "teamName": "Avalahalli Ninjas"
      },
      {
        "id": "part-2a46bef2",
        "name": "Shreyaa ND",
        "email": "shreyaa.nd24@gmail.com",
        "usn": "26UG1BYCS0105-T",
        "phone": "9632900771",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1016",
        "teamName": "Avalahalli Ninjas"
      },
      {
        "id": "part-e6bf5d5f",
        "name": "Kavya Sahu",
        "email": "kavyasahu008@gmail.com",
        "usn": "26UG1BYCS1053-T",
        "phone": "9027531423",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1016",
        "teamName": "Avalahalli Ninjas"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 16",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1017",
    "teamNumber": 17,
    "name": "Aura 999+",
    "leaderName": "Mayank Raj",
    "membersCount": 5,
    "members": [
      {
        "id": "part-999c6743",
        "name": "Mayank Raj",
        "email": "mayankraj7640204@gmail.com",
        "usn": "1BY25CS177",
        "phone": "7488423699",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1017",
        "teamName": "Aura 999+"
      },
      {
        "id": "part-38b6bb8e",
        "name": "Binit Kumar dash",
        "email": "binit@gmail.com",
        "usn": "1BY25CS074",
        "phone": "+91 89176 71338",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1017",
        "teamName": "Aura 999+"
      },
      {
        "id": "part-4ff56a8e",
        "name": "Thushar KS",
        "email": "thusharks@gmail.com",
        "usn": "1TE25CS315",
        "phone": "+91 95919 97179",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1017",
        "teamName": "Aura 999+"
      },
      {
        "id": "part-544c1bc6",
        "name": "Likith Reddy",
        "email": "likithreddy@gmail.com",
        "usn": "1BY25CS108",
        "phone": "+91 76749 05203",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1017",
        "teamName": "Aura 999+"
      },
      {
        "id": "part-f6b33b6b",
        "name": "Chinmay",
        "email": "chinmay@gmail.com",
        "usn": "1TE25CS114",
        "phone": "+91 87921 77479",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1017",
        "teamName": "Aura 999+"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 17",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1018",
    "teamNumber": 18,
    "name": "Sinners",
    "leaderName": "D Mitthun",
    "membersCount": 5,
    "members": [
      {
        "id": "part-8c103d8a",
        "name": "D Mitthun",
        "email": "dmitthun1@gmail.com",
        "usn": "26UG1BYAI0511-T",
        "phone": "9353609306",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1018",
        "teamName": "Sinners"
      },
      {
        "id": "part-6cbf2212",
        "name": "Harsha D Y",
        "email": "dyharsha13@gmail.com",
        "usn": "26UG1BYAI395-T",
        "phone": "7996695985",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1018",
        "teamName": "Sinners"
      },
      {
        "id": "part-7f2a231f",
        "name": "Vaageesha Thirtha P",
        "email": "vaageeshatheertha@gmail.com",
        "usn": "26UG1BYAI308-T",
        "phone": "6362165686",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1018",
        "teamName": "Sinners"
      },
      {
        "id": "part-8d797fd7",
        "name": "M S Pranay",
        "email": "mspranay893@gmail.com",
        "usn": "26UG1BYAI0509-T",
        "phone": "8519924790",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1018",
        "teamName": "Sinners"
      },
      {
        "id": "part-ea446f20",
        "name": "Rakshan M",
        "email": "rakshansirfu@gmail.com",
        "usn": "26UG1BYAI0512-T",
        "phone": "6364541256",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1018",
        "teamName": "Sinners"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 18",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1019",
    "teamNumber": 19,
    "name": "PENTA VOYAGE",
    "leaderName": "Rohini",
    "membersCount": 5,
    "members": [
      {
        "id": "part-1ad286f2",
        "name": "Rohini",
        "email": "rohinigirish2626@gmail.com",
        "usn": "26UG1BYAI041-T",
        "phone": "9187225561",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1019",
        "teamName": "PENTA VOYAGE"
      },
      {
        "id": "part-30e9bfa4",
        "name": "Nikhil",
        "email": "7at45nikhileshut@gmail.com",
        "usn": "26UG1BYEE014-T",
        "phone": "+91 86606 22922",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1019",
        "teamName": "PENTA VOYAGE"
      },
      {
        "id": "part-a1c292b9",
        "name": "Samarth",
        "email": "samkondurr@gmail.com",
        "usn": "26UG1BYAI095-T",
        "phone": "+91 90089 62385",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1019",
        "teamName": "PENTA VOYAGE"
      },
      {
        "id": "part-dc2bb366",
        "name": "Prachi",
        "email": "prachiagrwal2008@gmail.com",
        "usn": "26UG1BYAI111-T",
        "phone": "7061157968",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1019",
        "teamName": "PENTA VOYAGE"
      },
      {
        "id": "part-e6eaf6db",
        "name": "Sailesh",
        "email": "saileshsubbu@gmail.com",
        "usn": "26UG1BYEC009-T",
        "phone": "+91 95910 66541",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1019",
        "teamName": "PENTA VOYAGE"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 19",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1020",
    "teamNumber": 20,
    "name": "Survey cops",
    "leaderName": "Shivam Yadav",
    "membersCount": 5,
    "members": [
      {
        "id": "part-f1fe396d",
        "name": "Shivam Yadav",
        "email": "130107shivam@gmail.com",
        "usn": "26UG1BYCS1006-T",
        "phone": "6391364189",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1020",
        "teamName": "Survey cops"
      },
      {
        "id": "part-21a8bda9",
        "name": "Nishal P S",
        "email": "nishalpullan123@gmail.com",
        "usn": "26UG1BYCS0627-T",
        "phone": "9008347721",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1020",
        "teamName": "Survey cops"
      },
      {
        "id": "part-5c907853",
        "name": "Mithil Shriyan",
        "email": "mithilshriyan@gmail.com",
        "usn": "26UG1BYCS0625-T",
        "phone": "7410712267",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1020",
        "teamName": "Survey cops"
      },
      {
        "id": "part-85364773",
        "name": "Kushagra kumar yadav",
        "email": "kushagrak10419@gmail.com",
        "usn": "26UG1BYCS0962-T",
        "phone": "9180247235",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1020",
        "teamName": "Survey cops"
      },
      {
        "id": "part-a4300b65",
        "name": "Ganesh KH",
        "email": "ganeshkh5202008@gmail.com",
        "usn": "26UG1BYCS1202-T",
        "phone": "6362636124",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1020",
        "teamName": "Survey cops"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 20",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1021",
    "teamNumber": 21,
    "name": "R.chives",
    "leaderName": "Radhe S K",
    "membersCount": 5,
    "members": [
      {
        "id": "part-1bb9bc4a",
        "name": "Radhe S K",
        "email": "25ug1bycs0208@bmsit.in",
        "usn": "1BY25CS239",
        "phone": "9353143062",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1021",
        "teamName": "R.chives"
      },
      {
        "id": "part-2dfceca0",
        "name": "Hithaishi R Gowda",
        "email": "25ug1bycs1006@bmsit.in",
        "usn": "1TE25CS118",
        "phone": "9108973069",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1021",
        "teamName": "R.chives"
      },
      {
        "id": "part-403027d8",
        "name": "Prarthana C S",
        "email": "25ug1bycs0352@bmsit.in",
        "usn": "1TE25CS202",
        "phone": "7022101416",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1021",
        "teamName": "R.chives"
      },
      {
        "id": "part-5d518870",
        "name": "Thejashree K",
        "email": "25ug1bycs0896@bmsit.in",
        "usn": "1TD25CS320",
        "phone": "7892738367",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1021",
        "teamName": "R.chives"
      },
      {
        "id": "part-8803409d",
        "name": "Supriya B",
        "email": "supriyapriya22121@gmail.com",
        "usn": "26UG1BYCS497",
        "phone": "7022768149",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1021",
        "teamName": "R.chives"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 21",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1022",
    "teamNumber": 22,
    "name": "Meow meow",
    "leaderName": "Rakshitha KR",
    "membersCount": 5,
    "members": [
      {
        "id": "part-3d21e6f6",
        "name": "Rakshitha KR",
        "email": "25ug1byai245@bmsit.in",
        "usn": "1BY25AI188",
        "phone": "7975854547",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1022",
        "teamName": "Meow meow"
      },
      {
        "id": "part-02f2ff33",
        "name": "Nishkala",
        "email": "25ug1byai204@bmsit.in",
        "usn": "1BY25AI164",
        "phone": "9380466037",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1022",
        "teamName": "Meow meow"
      },
      {
        "id": "part-b196ffb6",
        "name": "Manjushree H",
        "email": "25ug1byai011@bmsit.in",
        "usn": "1BY25AI129",
        "phone": "8884424686",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1022",
        "teamName": "Meow meow"
      },
      {
        "id": "part-d76a7f95",
        "name": "Poorvika",
        "email": "25ug1byai033@bmsit.in",
        "usn": "1BY25AI171",
        "phone": "9535062885",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1022",
        "teamName": "Meow meow"
      },
      {
        "id": "part-ecf531eb",
        "name": "Kaveri AB",
        "email": "25ug1byai342@bmsit.in",
        "usn": "1BY25AI107",
        "phone": "8073305619",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1022",
        "teamName": "Meow meow"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 22",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1023",
    "teamNumber": 23,
    "name": "The Prime Five",
    "leaderName": "Naman kawad",
    "membersCount": 5,
    "members": [
      {
        "id": "part-6f346047",
        "name": "Naman kawad",
        "email": "namankawadk@gmail.com",
        "usn": "26UG1BYCS0502-T",
        "phone": "9606954504",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1023",
        "teamName": "The Prime Five"
      },
      {
        "id": "part-70e27a12",
        "name": "Harshith Gowda",
        "email": "harshithgowda1917@gmail.com",
        "usn": "26UG1BYCS0178-T",
        "phone": "8861330418",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1023",
        "teamName": "The Prime Five"
      },
      {
        "id": "part-a600903d",
        "name": "Deepti",
        "email": "harshithgowda1317@gmail.com",
        "usn": "26UG1BYCS0392-T",
        "phone": "7795829670",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1023",
        "teamName": "The Prime Five"
      },
      {
        "id": "part-a9b28c26",
        "name": "Ayush Shenoy",
        "email": "shenoyayush60@gmail.com",
        "usn": "26UG1BYCS0662-T",
        "phone": "8050213077",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1023",
        "teamName": "The Prime Five"
      },
      {
        "id": "part-eb3cb829",
        "name": "Chiranthan Gowda",
        "email": "goudachiranthan@hotmail.com",
        "usn": "26UG1BYCS0533-T",
        "phone": "7353739088",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1023",
        "teamName": "The Prime Five"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 23",
    "createdAt": "2026-10-06 08:29:32.387392"
  },
  {
    "id": "team-1024",
    "teamNumber": 24,
    "name": "Phoenix",
    "leaderName": "D Venkatesh Kumar",
    "membersCount": 5,
    "members": [
      {
        "id": "part-967861f8",
        "name": "D Venkatesh Kumar",
        "email": "vstudies2026@gmail.com",
        "usn": "26UG1BYAI047-T",
        "phone": "9606707090",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1024",
        "teamName": "Phoenix"
      },
      {
        "id": "part-3285f161",
        "name": "Anirudh CR",
        "email": "cranirudh611@gmail.com",
        "usn": "26UG1BYAI396-T",
        "phone": "9686400294",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1024",
        "teamName": "Phoenix"
      },
      {
        "id": "part-699bd983",
        "name": "Samarth Sudesh Shenoy",
        "email": "shenoysamarth926@gmail.com",
        "usn": "26UG1BYAI0548-T",
        "phone": "9743124977",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1024",
        "teamName": "Phoenix"
      },
      {
        "id": "part-715ec7be",
        "name": "Diganth Sairam Kothari",
        "email": "diganth126@gmail.com",
        "usn": "26UG1BYAI233-T",
        "phone": "9513736995",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1024",
        "teamName": "Phoenix"
      },
      {
        "id": "part-83c62201",
        "name": "Harshal A",
        "email": "harshal.ash22@gmail.com",
        "usn": "26UG1BYEE011-T",
        "phone": "9019959354",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1024",
        "teamName": "Phoenix"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 24",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1025",
    "teamNumber": 25,
    "name": "\u03c0-rates",
    "leaderName": "A Sanjana",
    "membersCount": 5,
    "members": [
      {
        "id": "part-f7fb8ac7",
        "name": "A Sanjana",
        "email": "sanjanaanandan07@gmail.com",
        "usn": "26UG1BYCS0004-T",
        "phone": "9945829763",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1025",
        "teamName": "\u03c0-rates"
      },
      {
        "id": "part-c29d689e",
        "name": "GOPISETTI VENKATA PRASOONA SIRI HASINI",
        "email": "gopisettisirii@gmail.com",
        "usn": "26UG1BYCS0693-T",
        "phone": "9676776998",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1025",
        "teamName": "\u03c0-rates"
      },
      {
        "id": "part-d39072fe",
        "name": "Neha Leona Prakash",
        "email": "nehaleona@gmail.com",
        "usn": "26UG1BYCS0185-T",
        "phone": "9845430149",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1025",
        "teamName": "\u03c0-rates"
      },
      {
        "id": "part-e707ea0e",
        "name": "Maria Cynthia Glory.A",
        "email": "mariacynthiaglory3@gmail.com",
        "usn": "26UG1BYCS0093-T",
        "phone": "7204879969",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1025",
        "teamName": "\u03c0-rates"
      },
      {
        "id": "part-f1f21936",
        "name": "Srushti Karadi",
        "email": "srushtikaradi17@gmail.com",
        "usn": "26UG1BYCS0032-T",
        "phone": "7676245745",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1025",
        "teamName": "\u03c0-rates"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 25",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1026",
    "teamNumber": 26,
    "name": "Kadur",
    "leaderName": "Trisha N kadur",
    "membersCount": 5,
    "members": [
      {
        "id": "part-0b418aa3",
        "name": "Trisha N kadur",
        "email": "trisha.kadur@gmail.com",
        "usn": "26UG1BYEC017-T",
        "phone": "+91 82962 36394",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1026",
        "teamName": "Kadur"
      },
      {
        "id": "part-1615e9be",
        "name": "Purvi Reddy H",
        "email": "purvireddy798@gmail.com",
        "usn": "26UG1BYAI029-T",
        "phone": "8088397016",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1026",
        "teamName": "Kadur"
      },
      {
        "id": "part-60b22f20",
        "name": "Aditi Y A",
        "email": "aditi3108ya@gmail.com",
        "usn": "26UG1BYEC022-T",
        "phone": "6360 511 881",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1026",
        "teamName": "Kadur"
      },
      {
        "id": "part-b0d794ed",
        "name": "Dinesh R",
        "email": "selvithamarai664@gmail.com",
        "usn": "26UG1BYCS0103-T",
        "phone": "+91 76768 28814",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1026",
        "teamName": "Kadur"
      },
      {
        "id": "part-bc0c15e2",
        "name": "Ibrahim",
        "email": "mohammedibrahimbanthanal@gmail.com",
        "usn": "26UG1BYME004-T",
        "phone": "8618582747",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1026",
        "teamName": "Kadur"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 26",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1027",
    "teamNumber": 27,
    "name": "ZeroShift",
    "leaderName": "D Venkata Abhishek",
    "membersCount": 5,
    "members": [
      {
        "id": "part-da54d276",
        "name": "D Venkata Abhishek",
        "email": "25ug1bycs0725@bmsit.in",
        "usn": "1TD25CS079",
        "phone": "7899616808",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1027",
        "teamName": "ZeroShift"
      },
      {
        "id": "part-7eabd2ab",
        "name": "Sanjana Ramesh H",
        "email": "25ug1bycs0086@bmsit.in",
        "usn": "1TE25CS257",
        "phone": "8073077769",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1027",
        "teamName": "ZeroShift"
      },
      {
        "id": "part-8da81249",
        "name": "Suparna Darsi",
        "email": "darsisuparna@gmail.com",
        "usn": "1BY25CS303",
        "phone": "8660901141",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1027",
        "teamName": "ZeroShift"
      },
      {
        "id": "part-9158a492",
        "name": "Anubhav kashyap",
        "email": "25ug1bycs0320@bmsit.in",
        "usn": "1BY25CS051",
        "phone": "9954282187",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1027",
        "teamName": "ZeroShift"
      },
      {
        "id": "part-bd460b39",
        "name": "Maneesha G",
        "email": "maneesha0629@gmail.com",
        "usn": "1BY25CS170",
        "phone": "7892425150",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1027",
        "teamName": "ZeroShift"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 27",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1028",
    "teamNumber": 28,
    "name": "Cipher",
    "leaderName": "Yashaswi G C",
    "membersCount": 5,
    "members": [
      {
        "id": "part-362ab24e",
        "name": "Yashaswi G C",
        "email": "gcyashaswi@gmail.com",
        "usn": "26UG1BYCS0011-T",
        "phone": "6360747713",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1028",
        "teamName": "Cipher"
      },
      {
        "id": "part-380bcae7",
        "name": "Mouli Nag",
        "email": "nagmouli53@gmail.com",
        "usn": "26UG1BYCS0314-T",
        "phone": "9394437227",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1028",
        "teamName": "Cipher"
      },
      {
        "id": "part-8946f781",
        "name": "M Nishitha",
        "email": "nishitham08@gmail.com",
        "usn": "26UG1BYCS1139-T",
        "phone": "8618229036",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1028",
        "teamName": "Cipher"
      },
      {
        "id": "part-c306adfa",
        "name": "Chinmayi S Gowda",
        "email": "chinmayisgowda38@gmail.com",
        "usn": "26UG1BYCS0640-T",
        "phone": "7353376234",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1028",
        "teamName": "Cipher"
      },
      {
        "id": "part-ca849162",
        "name": "U Himaja Reddy",
        "email": "uhimajaa@gmail.com",
        "usn": "26UG1BYCS0882-T",
        "phone": "9121267897",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1028",
        "teamName": "Cipher"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 28",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1029",
    "teamNumber": 29,
    "name": "ODDYSSEY ELITE",
    "leaderName": "Varun Tej C",
    "membersCount": 5,
    "members": [
      {
        "id": "part-bdbb06b7",
        "name": "Varun Tej C",
        "email": "varuntejc149@gmail.com",
        "usn": "26UG1BYCS0872-T",
        "phone": "8886502050",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1029",
        "teamName": "ODDYSSEY ELITE"
      },
      {
        "id": "part-0e510adc",
        "name": "Marati Naga Koushik",
        "email": "dynamicgamers500@gmail.com",
        "usn": "26UG1BYCS0933-T",
        "phone": "9908187329",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1029",
        "teamName": "ODDYSSEY ELITE"
      },
      {
        "id": "part-94a403f4",
        "name": "Hrithika Dayala",
        "email": "hrithikareddy777@gmail.com",
        "usn": "26UG1BYCS0890-T",
        "phone": "8951278928",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1029",
        "teamName": "ODDYSSEY ELITE"
      },
      {
        "id": "part-d43d535d",
        "name": "Prema Spandana N",
        "email": "nasireddypremaspandana13@gmail.com",
        "usn": "26UG1BYCS0610-T",
        "phone": "6364516097",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1029",
        "teamName": "ODDYSSEY ELITE"
      },
      {
        "id": "part-d524c4a0",
        "name": "Rashmi",
        "email": "rashmivibhtui30@gmail.com",
        "usn": "26UG1BY0110-T",
        "phone": "9481720555",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1029",
        "teamName": "ODDYSSEY ELITE"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 29",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1030",
    "teamNumber": 30,
    "name": "Apex Solvers",
    "leaderName": "Anushka Uppin",
    "membersCount": 5,
    "members": [
      {
        "id": "part-4591ef63",
        "name": "Anushka Uppin",
        "email": "anushkauppin@gmail.com",
        "usn": "1BY25AI036",
        "phone": "+91 866 043 7880",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1030",
        "teamName": "Apex Solvers"
      },
      {
        "id": "part-06fada6a",
        "name": "Suprith S",
        "email": "shettysuprith04@gmail.com",
        "usn": "1BY25AI255",
        "phone": "7483 642 754",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1030",
        "teamName": "Apex Solvers"
      },
      {
        "id": "part-9d8fce08",
        "name": "Apeksha Satish Devadiga",
        "email": "devadigaapeksha8@gmail.com",
        "usn": "1BY25AI037",
        "phone": "9108170289",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1030",
        "teamName": "Apex Solvers"
      },
      {
        "id": "part-b5e8daf2",
        "name": "Vemula Greeshma Choudhary",
        "email": "vemulagreeshma92@gmail.com",
        "usn": "1BY25AI273",
        "phone": "+91 91105 28033",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1030",
        "teamName": "Apex Solvers"
      },
      {
        "id": "part-c6984231",
        "name": "Suriya Narayanan J",
        "email": "suriyanarayanan176@gmail.com",
        "usn": "1BY25AI256",
        "phone": "8884969458",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1030",
        "teamName": "Apex Solvers"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 30",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1031",
    "teamNumber": 31,
    "name": "Team Heisenberg",
    "leaderName": "Shashank S",
    "membersCount": 5,
    "members": [
      {
        "id": "part-0a342c5f",
        "name": "Shashank S",
        "email": "shashanks1072008@gmail.com",
        "usn": "26UG1BYBS023-T",
        "phone": "6366955622",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1031",
        "teamName": "Team Heisenberg"
      },
      {
        "id": "part-0833e738",
        "name": "Sujan",
        "email": "nagasujan1981@gmail.com",
        "usn": "26UG1BYAI081-T",
        "phone": "9148015161",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1031",
        "teamName": "Team Heisenberg"
      },
      {
        "id": "part-2128b57c",
        "name": "Sukush",
        "email": "gvsukush@gmail.com",
        "usn": "26UG1BYCS0125-T",
        "phone": "9989969280",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1031",
        "teamName": "Team Heisenberg"
      },
      {
        "id": "part-804bc265",
        "name": "Vishwas",
        "email": "vishwaskandhan0@gmail.com",
        "usn": "26UG1BYCS0126-T",
        "phone": "8277092857",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1031",
        "teamName": "Team Heisenberg"
      },
      {
        "id": "part-f79358d8",
        "name": "Kokil Reddy",
        "email": "kokilreddy027@gmail.com",
        "usn": "26UG1BYCS0124-T",
        "phone": "8147828096",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1031",
        "teamName": "Team Heisenberg"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 31",
    "createdAt": "2026-10-06 10:18:46.216978"
  },
  {
    "id": "team-1032",
    "teamNumber": 32,
    "name": "Team Mirage",
    "leaderName": "Parasmani Kushwaha",
    "membersCount": 5,
    "members": [
      {
        "id": "part-08b53223",
        "name": "Parasmani Kushwaha",
        "email": "parasmanikushwaha4@gmail.com",
        "usn": "1BY25CS215",
        "phone": "8153011907",
        "role": "Leader",
        "checkedIn": false,
        "teamId": "team-1032",
        "teamName": "Team Mirage"
      },
      {
        "id": "part-3a49ff71",
        "name": "Vernit Gupta",
        "email": "guptavernit2@gmail.com",
        "usn": "1TD25CS337",
        "phone": "9305808024",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1032",
        "teamName": "Team Mirage"
      },
      {
        "id": "part-65e54243",
        "name": "Archit Kumar",
        "email": "architk760@gmail.com",
        "usn": "1BY25EC025",
        "phone": "7018097453",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1032",
        "teamName": "Team Mirage"
      },
      {
        "id": "part-69de7fa4",
        "name": "Ayush Kumar Yadav",
        "email": "ayushyadav170707@gmail.com",
        "usn": "1BY25AI043",
        "phone": "7803077193",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1032",
        "teamName": "Team Mirage"
      },
      {
        "id": "part-9f571284",
        "name": "Divyansh Singh",
        "email": "divyansh.singh.mirage@bmsit.in",
        "usn": "1BY24CS-DIVYANSH",
        "phone": "9999991032",
        "role": "Member",
        "checkedIn": false,
        "teamId": "team-1032",
        "teamName": "Team Mirage"
      }
    ],
    "status": "Registered",
    "currentRound": 1,
    "isQualifiedForNextRound": false,
    "totalScore": 0.0,
    "assignedTable": "Table 32",
    "createdAt": "2026-10-06 14:30:09"
  }
];

export const MOCK_ROUNDS: RoundInfo[] = [
  {
    roundNumber: 1,
    name: 'The ODDyssey Protocol',
    codename: 'ROUND_1_ODDYSSEY_PROTOCOL',
    description: 'Physical campus puzzle hunt across 3 checkpoints. 32 teams compete; top 16 qualify.',
    initialTeamsCount: 32,
    qualifyingTeamsCount: 16,
    status: 'In Progress',
    startedAt: '2026-10-06T06:42:28.815Z',
    location: 'Campus Grounds & Quadrangles',
  },
  {
    roundNumber: 2,
    name: 'Cabo - The Memory Heist',
    codename: 'ROUND_2_CABO_THE_MEMORY_HEIST',
    description: 'Strategic card memory and deduction tournament. 16 qualified teams from R1 compete across 3 games; top 8 qualify.',
    initialTeamsCount: 16,
    qualifyingTeamsCount: 8,
    status: 'Scheduled',
    location: 'Main Auditorium Annex',
  },
  {
    roundNumber: 3,
    name: 'The Black Market',
    codename: 'ROUND_3_BLACK_MARKET',
    description: 'Volatile resource economy, asset auction, and code fragment decryption. 8 teams; top 4 qualify.',
    initialTeamsCount: 8,
    qualifyingTeamsCount: 4,
    status: 'Scheduled',
    location: 'Commerce Wing Hub',
  },
  {
    roundNumber: 4,
    name: 'The Legal Battle',
    codename: 'ROUND_4_LEGAL_BATTLE',
    description: '4 finalist squads face off in 2 semifinal legal court battles.',
    initialTeamsCount: 4,
    qualifyingTeamsCount: 1,
    status: 'Scheduled',
    location: 'Moot Court Hall',
  },
  {
    roundNumber: 5,
    name: 'Grand Finale',
    codename: 'GRAND_FINALE',
    description: 'Finalists face the Grand Faculty Tribunal and unmask undercover agents.',
    initialTeamsCount: 3,
    qualifyingTeamsCount: 1,
    status: 'Scheduled',
    location: 'Main Auditorium Stage',
  },
];

export const MOCK_PROGRESSION_STEPS: RoundProgressionStep[] = [
  { roundNumber: 1, name: 'The ODDyssey Protocol', totalPool: 32, qualifyingCount: 16, status: 'In Progress' },
  { roundNumber: 2, name: 'Cabo: The Memory Heist', totalPool: 16, qualifyingCount: 8, status: 'Scheduled' },
  { roundNumber: 3, name: 'The Black Market', totalPool: 8, qualifyingCount: 4, status: 'Scheduled' },
  { roundNumber: 4, name: 'The Legal Battle', totalPool: 4, qualifyingCount: 2, status: 'Scheduled' },
  { roundNumber: 5, name: 'Grand Finale', totalPool: 2, qualifyingCount: 1, status: 'Scheduled' },
];

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  totalTeams: 32,
  totalParticipants: 160,
  currentRoundName: 'Round 1: Clue Hunt',
  currentRoundNumber: 1,
  currentRoundStatus: 'In Progress',
  qualifiedTeamsTarget: 16,
  activeTeamsRemaining: 32,
  eventProgressPercentage: 20,
  checkedInTeams: 0,
  checkedInParticipants: 0,
  completeRosterTeams: 32,
  incompleteRosterTeams: 0,
  agentsAssigned: 32,
  fragmentsDiscovered: 0,
  totalFragments: 32,
};

export const MOCK_RECENT_ACTIVITIES: ActivityLogItem[] = [
  {
    id: 'act-1',
    timestamp: new Date().toISOString(),
    category: 'system',
    title: 'Round 1 In Progress',
    description: '32 official teams competing across 3 checkpoint routes.',
    badgeType: 'info',
  }
];
