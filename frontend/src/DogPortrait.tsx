export type DogBreed = "bulldog" | "golden" | "terrier" | "shepherd" | "cocker";

type DogArt = {
  name: string;
  head: string;
  earLeft: string;
  earRight: string;
  earInnerLeft: string;
  earInnerRight: string;
  muzzle: string;
  muzzleColor: string;
  fur: string;
  furShadow: string;
  earColor: string;
  eyeY: number;
  eyeGap: number;
  noseWidth: number;
  background: string;
  scarf: string;
  mark?: string;
};

const DOG_ART: Record<DogBreed, DogArt> = {
  bulldog: {
    name: "Handsome Dan-inspired bulldog",
    head: "M30 58 C27 43 36 30 50 29 C56 21 72 21 79 29 C94 31 101 43 98 60 L96 81 C93 99 78 108 64 108 C48 108 34 98 31 81 Z",
    earLeft: "M36 42 C25 29 18 28 16 39 C14 49 22 57 34 59 Z",
    earRight: "M91 42 C102 29 109 28 112 39 C114 49 105 57 94 59 Z",
    earInnerLeft: "M33 42 C27 36 24 36 23 41 C23 46 27 49 33 51 Z",
    earInnerRight: "M94 42 C100 36 104 36 105 41 C105 46 100 49 94 51 Z",
    muzzle: "M37 74 C39 65 49 63 57 69 C61 66 67 66 71 69 C80 63 90 65 92 74 C94 86 82 96 64 97 C47 96 35 87 37 74 Z",
    muzzleColor: "#e8d6bd",
    fur: "#b5b8b0",
    furShadow: "#929a94",
    earColor: "#888f8c",
    eyeY: 59,
    eyeGap: 17,
    noseWidth: 17,
    background: "#f2ded1",
    scarf: "#ad493e",
    mark: "M45 44 Q52 48 59 44 M69 44 Q77 48 83 44 M56 54 Q64 57 72 54",
  },
  golden: {
    name: "golden retriever",
    head: "M36 51 C37 34 49 26 64 26 C81 26 92 37 92 54 L90 78 C87 95 77 105 64 105 C50 105 40 95 37 78 Z",
    earLeft: "M40 44 C27 35 19 41 21 61 C22 80 31 92 41 87 C46 80 44 59 40 44 Z",
    earRight: "M88 44 C101 35 109 41 107 61 C106 80 97 92 87 87 C82 80 84 59 88 44 Z",
    earInnerLeft: "M38 49 C30 45 28 49 29 62 C30 73 34 79 39 78 Z",
    earInnerRight: "M90 49 C98 45 100 49 99 62 C98 73 94 79 89 78 Z",
    muzzle: "M43 70 C45 59 55 57 64 64 C74 57 84 60 86 71 C88 84 79 92 64 93 C49 92 40 83 43 70 Z",
    muzzleColor: "#f4e5c9",
    fur: "#d5a24e",
    furShadow: "#b98235",
    earColor: "#b57831",
    eyeY: 58,
    eyeGap: 16,
    noseWidth: 13,
    background: "#f4e9ce",
    scarf: "#77915e",
  },
  terrier: {
    name: "wire-haired terrier",
    head: "M37 50 L30 28 Q29 22 35 25 L54 39 Q64 34 74 39 L93 25 Q99 22 98 29 L91 51 C95 62 91 80 85 91 Q76 104 63 103 Q48 103 40 91 C33 79 31 62 37 50 Z",
    earLeft: "M38 48 L30 28 Q29 22 35 25 L52 39 Z",
    earRight: "M90 48 L98 28 Q99 22 93 25 L76 39 Z",
    earInnerLeft: "M39 42 L34 31 L47 40 Z",
    earInnerRight: "M89 42 L94 31 L81 40 Z",
    muzzle: "M45 71 C48 62 56 60 64 66 C73 60 81 63 84 72 C86 85 77 93 64 95 C50 93 42 84 45 71 Z",
    muzzleColor: "#eee0c8",
    fur: "#c4a171",
    furShadow: "#9c754a",
    earColor: "#a47b51",
    eyeY: 59,
    eyeGap: 15,
    noseWidth: 12,
    background: "#e9e8d7",
    scarf: "#4c7190",
    mark: "M42 50 L48 45 L53 50 M75 50 L80 45 L85 50",
  },
  shepherd: {
    name: "German shepherd",
    head: "M36 50 L27 18 Q26 12 33 18 L54 36 Q64 31 74 36 L95 18 Q102 12 101 18 L92 51 C96 64 91 83 84 94 Q75 105 64 105 Q50 105 41 94 C34 82 31 64 36 50 Z",
    earLeft: "M38 48 L28 19 Q27 14 33 19 L53 37 Z",
    earRight: "M90 48 L100 19 Q101 14 95 19 L75 37 Z",
    earInnerLeft: "M39 41 L33 24 L48 38 Z",
    earInnerRight: "M89 41 L95 24 L80 38 Z",
    muzzle: "M45 72 C47 62 56 58 64 65 C72 58 81 62 84 72 C87 84 77 93 64 95 C51 93 42 84 45 72 Z",
    muzzleColor: "#e9d5b4",
    fur: "#c59050",
    furShadow: "#765341",
    earColor: "#493e37",
    eyeY: 57,
    eyeGap: 16,
    noseWidth: 12,
    background: "#e5e8d9",
    scarf: "#597653",
    mark: "M43 47 Q64 57 85 47 L81 61 Q64 54 47 61 Z",
  },
  cocker: {
    name: "cocker spaniel",
    head: "M37 51 C38 36 48 27 62 27 C77 24 90 36 91 51 C94 68 90 84 81 96 Q73 106 63 106 Q50 105 42 95 C34 83 32 67 37 51 Z",
    earLeft: "M39 45 C23 35 17 44 18 66 C18 88 25 105 37 105 C45 98 46 72 43 52 Z",
    earRight: "M89 45 C105 35 111 44 110 66 C110 88 103 105 91 105 C83 98 82 72 85 52 Z",
    earInnerLeft: "M36 51 C27 47 25 54 26 70 C27 86 30 94 36 95 C41 85 40 65 36 51 Z",
    earInnerRight: "M92 51 C101 47 103 54 102 70 C101 86 98 94 92 95 C87 85 88 65 92 51 Z",
    muzzle: "M44 70 C47 60 56 58 64 65 C72 58 81 61 84 71 C87 85 77 94 64 95 C50 94 41 84 44 70 Z",
    muzzleColor: "#efdcc2",
    fur: "#b86e4e",
    furShadow: "#824a3e",
    earColor: "#9e5743",
    eyeY: 58,
    eyeGap: 16,
    noseWidth: 12,
    background: "#f0dfd6",
    scarf: "#a7445e",
    mark: "M45 42 Q52 47 58 43 M70 43 Q77 47 83 42",
  },
};

type DogPortraitProps = {
  breed: DogBreed;
  size?: number;
  className?: string;
};

export default function DogPortrait({ breed, size = 56, className = "" }: DogPortraitProps) {
  const dog = DOG_ART[breed];
  const eyeLeft = 64 - dog.eyeGap;
  const eyeRight = 64 + dog.eyeGap;
  return (
    <svg
      className={"dog-portrait " + className}
      width={size}
      height={size}
      viewBox="0 0 128 128"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="64" cy="64" r="61" fill={dog.background} />
      <circle cx="64" cy="64" r="56" stroke="#fffaf0" strokeWidth="2" strokeDasharray="2 4" />
      <ellipse cx="64" cy="116" rx="34" ry="8" fill="#514338" fillOpacity=".10" />

      <path d={dog.earLeft} fill={dog.earColor} stroke="#493f36" strokeWidth="3" strokeLinejoin="round" />
      <path d={dog.earRight} fill={dog.earColor} stroke="#493f36" strokeWidth="3" strokeLinejoin="round" />
      <path d={dog.earInnerLeft} fill={dog.furShadow} stroke="#493f36" strokeWidth="1.4" strokeLinejoin="round" />
      <path d={dog.earInnerRight} fill={dog.furShadow} stroke="#493f36" strokeWidth="1.4" strokeLinejoin="round" />

      <path d="M43 87 Q40 106 48 118 L80 118 Q88 104 85 87 Z" fill={dog.furShadow} stroke="#493f36" strokeWidth="3" strokeLinejoin="round" />
      <path d={dog.head} fill={dog.fur} stroke="#493f36" strokeWidth="3.5" strokeLinejoin="round" />
      {dog.mark && <path d={dog.mark} fill="none" stroke={breed === "shepherd" ? "#493e37" : dog.furShadow} strokeWidth={breed === "shepherd" ? 7 : 2.2} strokeLinecap="round" strokeLinejoin="round" />}

      {breed === "bulldog" && (
        <>
          <path d="M46 65 Q54 61 60 66 M68 66 Q76 61 83 65" stroke="#777d79" strokeWidth="2" strokeLinecap="round" />
          <path d="M49 80 Q54 76 59 80 M69 80 Q74 76 79 80" stroke="#b09b80" strokeWidth="1.5" strokeLinecap="round" />
        </>
      )}
      {breed === "terrier" && (
        <path d="M38 55 L43 47 L47 53 L53 45 L58 52 M70 52 L76 45 L81 53 L86 47 L91 56" fill="none" stroke="#f1e3c7" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      )}
      {breed === "cocker" && (
        <path d="M39 61 C34 74 35 91 42 99 M89 61 C94 74 93 91 86 99" fill="none" stroke="#d89a74" strokeWidth="2" strokeLinecap="round" />
      )}

      <ellipse cx={eyeLeft} cy={dog.eyeY} rx={breed === "bulldog" ? 4.4 : 3.6} ry="4.8" fill="#342f2a" />
      <ellipse cx={eyeRight} cy={dog.eyeY} rx={breed === "bulldog" ? 4.4 : 3.6} ry="4.8" fill="#342f2a" />
      <circle cx={eyeLeft - 1} cy={dog.eyeY - 1.5} r="1.15" fill="#fff8e9" />
      <circle cx={eyeRight - 1} cy={dog.eyeY - 1.5} r="1.15" fill="#fff8e9" />

      <path d={dog.muzzle} fill={dog.muzzleColor} stroke="#493f36" strokeWidth="2.4" strokeLinejoin="round" />
      <path d={breed === "bulldog" ? "M53 73 Q64 67 75 73 Q73 83 64 84 Q55 83 53 73 Z" : "M56 70 Q64 66 72 70 Q71 78 64 79 Q57 78 56 70 Z"} fill="#302d29" stroke="#493f36" strokeWidth="1.5" />
      <path d="M64 81 L64 86 M64 86 Q59 91 55 87 M64 86 Q69 91 73 87" stroke="#55433b" strokeWidth="1.8" strokeLinecap="round" />
      {breed === "bulldog" && <path d="M53 94 Q64 99 75 94" stroke="#756257" strokeWidth="2.3" strokeLinecap="round" />}

      <path d="M43 103 Q64 110 85 103 L80 117 Q64 125 48 117 Z" fill={dog.scarf} stroke="#493f36" strokeWidth="2.6" strokeLinejoin="round" />
      <path d="M49 108 Q64 114 79 108" stroke="#fff5df" strokeOpacity=".75" strokeWidth="1.7" strokeLinecap="round" />
      <circle cx="64" cy="116" r="3.1" fill="#e4c47c" stroke="#493f36" strokeWidth="1.4" />
      <path d="M43 37 Q64 20 85 37" stroke="#fff6e6" strokeOpacity=".5" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
