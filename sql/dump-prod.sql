--
-- PostgreSQL database dump
--

-- Dumped from database version 15.0 (Debian 15.0-1.pgdg110+1)
-- Dumped by pg_dump version 15.0 (Debian 15.0-1.pgdg110+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: prod; Type: SCHEMA; Schema: -; Owner: cmcismaster
--

CREATE SCHEMA prod;


ALTER SCHEMA prod OWNER TO cmcismaster;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity; Type: TABLE; Schema: prod; Owner: cmcismaster
--

CREATE TABLE prod.activity (
    activity_id integer NOT NULL,
    title character varying(200),
    place integer NOT NULL,
    vizitors smallint,
    showtime timestamp without time zone,
    description text,
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE prod.activity OWNER TO cmcismaster;

--
-- Name: activity_activity_id_seq; Type: SEQUENCE; Schema: prod; Owner: cmcismaster
--

CREATE SEQUENCE prod.activity_activity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE prod.activity_activity_id_seq OWNER TO cmcismaster;

--
-- Name: activity_activity_id_seq; Type: SEQUENCE OWNED BY; Schema: prod; Owner: cmcismaster
--

ALTER SEQUENCE prod.activity_activity_id_seq OWNED BY prod.activity.activity_id;


--
-- Name: booking; Type: TABLE; Schema: prod; Owner: cmcismaster
--

CREATE TABLE prod.booking (
    client_id bigint NOT NULL,
    activity_id integer NOT NULL,
    actual boolean NOT NULL,
    modified timestamp without time zone DEFAULT now() NOT NULL,
    changes smallint DEFAULT 0,
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE prod.booking OWNER TO cmcismaster;

--
-- Name: COLUMN booking.client_id; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.booking.client_id IS 'telegram user identifier';


--
-- Name: COLUMN booking.activity_id; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.booking.activity_id IS 'activity identifier';


--
-- Name: COLUMN booking.actual; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.booking.actual IS 'Booking actuality';


--
-- Name: COLUMN booking.modified; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.booking.modified IS 'last modified timestamp';


--
-- Name: COLUMN booking.changes; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.booking.changes IS 'Number of changes';


--
-- Name: client; Type: TABLE; Schema: prod; Owner: cmcismaster
--

CREATE TABLE prod.client (
    client_id bigint NOT NULL,
    username character varying(100),
    first_name character varying(100),
    last_name character varying(100),
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE prod.client OWNER TO cmcismaster;

--
-- Name: COLUMN client.client_id; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.client.client_id IS 'telegram user identifier';


--
-- Name: place; Type: TABLE; Schema: prod; Owner: cmcismaster
--

CREATE TABLE prod.place (
    place_id integer NOT NULL,
    description text,
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE prod.place OWNER TO cmcismaster;

--
-- Name: COLUMN place.place_id; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.place.place_id IS 'Place identifier';


--
-- Name: COLUMN place.description; Type: COMMENT; Schema: prod; Owner: cmcismaster
--

COMMENT ON COLUMN prod.place.description IS 'Place description';


--
-- Name: place_place_id_seq; Type: SEQUENCE; Schema: prod; Owner: cmcismaster
--

CREATE SEQUENCE prod.place_place_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE prod.place_place_id_seq OWNER TO cmcismaster;

--
-- Name: place_place_id_seq; Type: SEQUENCE OWNED BY; Schema: prod; Owner: cmcismaster
--

ALTER SEQUENCE prod.place_place_id_seq OWNED BY prod.place.place_id;


--
-- Name: activity activity_id; Type: DEFAULT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.activity ALTER COLUMN activity_id SET DEFAULT nextval('prod.activity_activity_id_seq'::regclass);


--
-- Name: place place_id; Type: DEFAULT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.place ALTER COLUMN place_id SET DEFAULT nextval('prod.place_place_id_seq'::regclass);


--
-- Data for Name: activity; Type: TABLE DATA; Schema: prod; Owner: cmcismaster
--

COPY prod.activity (activity_id, title, place, vizitors, showtime, description, created) FROM stdin;
\.


--
-- Data for Name: booking; Type: TABLE DATA; Schema: prod; Owner: cmcismaster
--

COPY prod.booking (client_id, activity_id, actual, modified, changes, created) FROM stdin;
\.


--
-- Data for Name: client; Type: TABLE DATA; Schema: prod; Owner: cmcismaster
--

COPY prod.client (client_id, username, first_name, last_name, created) FROM stdin;
\.


--
-- Data for Name: place; Type: TABLE DATA; Schema: prod; Owner: cmcismaster
--

COPY prod.place (place_id, description, created) FROM stdin;
\.


--
-- Name: activity_activity_id_seq; Type: SEQUENCE SET; Schema: prod; Owner: cmcismaster
--

SELECT pg_catalog.setval('prod.activity_activity_id_seq', 1, false);


--
-- Name: place_place_id_seq; Type: SEQUENCE SET; Schema: prod; Owner: cmcismaster
--

SELECT pg_catalog.setval('prod.place_place_id_seq', 1, false);


--
-- Name: activity activity_pk; Type: CONSTRAINT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.activity
    ADD CONSTRAINT activity_pk PRIMARY KEY (activity_id);


--
-- Name: client client_pk; Type: CONSTRAINT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.client
    ADD CONSTRAINT client_pk PRIMARY KEY (client_id);


--
-- Name: place place_pk; Type: CONSTRAINT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.place
    ADD CONSTRAINT place_pk PRIMARY KEY (place_id);


--
-- Name: activity activity_fk; Type: FK CONSTRAINT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.activity
    ADD CONSTRAINT activity_fk FOREIGN KEY (place) REFERENCES prod.place(place_id);


--
-- Name: booking booking_fk; Type: FK CONSTRAINT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.booking
    ADD CONSTRAINT booking_fk FOREIGN KEY (client_id) REFERENCES prod.client(client_id);


--
-- Name: booking booking_fk_1; Type: FK CONSTRAINT; Schema: prod; Owner: cmcismaster
--

ALTER TABLE ONLY prod.booking
    ADD CONSTRAINT booking_fk_1 FOREIGN KEY (activity_id) REFERENCES prod.activity(activity_id);


--
-- PostgreSQL database dump complete
--

