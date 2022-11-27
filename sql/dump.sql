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
-- Name: harpy; Type: SCHEMA; Schema: -; Owner: cmcismaster
--

CREATE SCHEMA harpy;


ALTER SCHEMA harpy OWNER TO cmcismaster;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity; Type: TABLE; Schema: harpy; Owner: cmcismaster
--

CREATE TABLE harpy.activity (
    activity_id integer NOT NULL,
    title character varying(200),
    place integer NOT NULL,
    max_visitors smallint,
    showtime timestamp without time zone,
    openreg timestamp without time zone,
    info text,
    active boolean DEFAULT true,
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE harpy.activity OWNER TO cmcismaster;

--
-- Name: COLUMN activity.title; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.activity.title IS 'Activity title';


--
-- Name: COLUMN activity.place; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.activity.place IS 'Activity place info';


--
-- Name: COLUMN activity.max_visitors; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.activity.max_visitors IS 'Max number of visitors';


--
-- Name: COLUMN activity.showtime; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.activity.showtime IS 'Date and time of show';


--
-- Name: COLUMN activity.openreg; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.activity.openreg IS 'Start registration date & time';


--
-- Name: COLUMN activity.info; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.activity.info IS 'Addtitional information';


--
-- Name: COLUMN activity.active; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.activity.active IS 'Activity status';


--
-- Name: activity_activity_id_seq; Type: SEQUENCE; Schema: harpy; Owner: cmcismaster
--

CREATE SEQUENCE harpy.activity_activity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE harpy.activity_activity_id_seq OWNER TO cmcismaster;

--
-- Name: activity_activity_id_seq; Type: SEQUENCE OWNED BY; Schema: harpy; Owner: cmcismaster
--

ALTER SEQUENCE harpy.activity_activity_id_seq OWNED BY harpy.activity.activity_id;


--
-- Name: booking; Type: TABLE; Schema: harpy; Owner: cmcismaster
--

CREATE TABLE harpy.booking (
    client_id bigint NOT NULL,
    activity_id integer NOT NULL,
    actual boolean NOT NULL,
    modified timestamp without time zone DEFAULT now() NOT NULL,
    num_changes smallint DEFAULT 0,
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE harpy.booking OWNER TO cmcismaster;

--
-- Name: COLUMN booking.client_id; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.booking.client_id IS 'Telegram user identifier';


--
-- Name: COLUMN booking.activity_id; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.booking.activity_id IS 'Activity identifier';


--
-- Name: COLUMN booking.actual; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.booking.actual IS 'Booking actuality';


--
-- Name: COLUMN booking.modified; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.booking.modified IS 'Last modified timestamp';


--
-- Name: COLUMN booking.num_changes; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.booking.num_changes IS 'Number of changes';


--
-- Name: client; Type: TABLE; Schema: harpy; Owner: cmcismaster
--

CREATE TABLE harpy.client (
    client_id bigint NOT NULL,
    specname character varying(100),
    username character varying(100),
    first_name character varying(100),
    last_name character varying(100),
    is_admin boolean,
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE harpy.client OWNER TO cmcismaster;

--
-- Name: COLUMN client.client_id; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.client.client_id IS 'Telegram user identifier';


--
-- Name: COLUMN client.is_admin; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.client.is_admin IS 'Bot administrator status';


--
-- Name: place; Type: TABLE; Schema: harpy; Owner: cmcismaster
--

CREATE TABLE harpy.place (
    place_id integer NOT NULL,
    addr character varying(200),
    info text,
    created timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE harpy.place OWNER TO cmcismaster;

--
-- Name: COLUMN place.place_id; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.place.place_id IS 'Place identifier';


--
-- Name: COLUMN place.info; Type: COMMENT; Schema: harpy; Owner: cmcismaster
--

COMMENT ON COLUMN harpy.place.info IS 'Addtitional info';


--
-- Name: place_place_id_seq; Type: SEQUENCE; Schema: harpy; Owner: cmcismaster
--

CREATE SEQUENCE harpy.place_place_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE harpy.place_place_id_seq OWNER TO cmcismaster;

--
-- Name: place_place_id_seq; Type: SEQUENCE OWNED BY; Schema: harpy; Owner: cmcismaster
--

ALTER SEQUENCE harpy.place_place_id_seq OWNED BY harpy.place.place_id;


--
-- Name: activity activity_id; Type: DEFAULT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.activity ALTER COLUMN activity_id SET DEFAULT nextval('harpy.activity_activity_id_seq'::regclass);


--
-- Name: place place_id; Type: DEFAULT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.place ALTER COLUMN place_id SET DEFAULT nextval('harpy.place_place_id_seq'::regclass);


--
-- Name: activity activity_pk; Type: CONSTRAINT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.activity
    ADD CONSTRAINT activity_pk PRIMARY KEY (activity_id);


--
-- Name: booking booking_un; Type: CONSTRAINT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.booking
    ADD CONSTRAINT booking_un UNIQUE (client_id, activity_id);


--
-- Name: client client_pk; Type: CONSTRAINT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.client
    ADD CONSTRAINT client_pk PRIMARY KEY (client_id);


--
-- Name: place place_pk; Type: CONSTRAINT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.place
    ADD CONSTRAINT place_pk PRIMARY KEY (place_id);


--
-- Name: activity activity_fk; Type: FK CONSTRAINT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.activity
    ADD CONSTRAINT activity_fk FOREIGN KEY (place) REFERENCES harpy.place(place_id);


--
-- Name: booking booking_fk; Type: FK CONSTRAINT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.booking
    ADD CONSTRAINT booking_fk FOREIGN KEY (client_id) REFERENCES harpy.client(client_id);


--
-- Name: booking booking_fk_1; Type: FK CONSTRAINT; Schema: harpy; Owner: cmcismaster
--

ALTER TABLE ONLY harpy.booking
    ADD CONSTRAINT booking_fk_1 FOREIGN KEY (activity_id) REFERENCES harpy.activity(activity_id);


--
-- PostgreSQL database dump complete
--

