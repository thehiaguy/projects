// Session uniqueness
CREATE CONSTRAINT session_id_unique IF NOT EXISTS
FOR (s:Session) REQUIRE s.sessionId IS UNIQUE;

// Utterance uniqueness
CREATE CONSTRAINT utterance_id_unique IF NOT EXISTS
FOR (u:Utterance) REQUIRE u.utteranceId IS UNIQUE;

// ProsodyFrame uniqueness
CREATE CONSTRAINT prosody_frame_id_unique IF NOT EXISTS
FOR (p:ProsodyFrame) REQUIRE p.frameId IS UNIQUE;

// Concept composite uniqueness: (sessionId, canonical) per label
CREATE CONSTRAINT person_unique IF NOT EXISTS
FOR (n:Person) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;

CREATE CONSTRAINT trigger_unique IF NOT EXISTS
FOR (n:Trigger) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;

CREATE CONSTRAINT emotion_unique IF NOT EXISTS
FOR (n:Emotion) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;

CREATE CONSTRAINT belief_unique IF NOT EXISTS
FOR (n:Belief) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;

CREATE CONSTRAINT need_unique IF NOT EXISTS
FOR (n:Need) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;

CREATE CONSTRAINT goal_unique IF NOT EXISTS
FOR (n:Goal) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;

CREATE CONSTRAINT action_unique IF NOT EXISTS
FOR (n:Action) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;

CREATE CONSTRAINT event_unique IF NOT EXISTS
FOR (n:Event) REQUIRE (n.sessionId, n.canonical) IS UNIQUE;
