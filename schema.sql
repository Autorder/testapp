--
-- PostgreSQL database dump
--

\restrict 30IyscYGXu4Am5h81nVttANDd0LrxBghsMCthBfLVc5CMxORSHqyaBDbWYPTQ7G

-- Dumped from database version 14.19 (Homebrew)
-- Dumped by pg_dump version 14.19 (Homebrew)

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: testapp_appointments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.testapp_appointments (
    id integer NOT NULL,
    title text NOT NULL,
    date_text text NOT NULL,
    time_text text NOT NULL,
    location text,
    notes text,
    status text DEFAULT 'planned'::text NOT NULL,
    updated_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    owner_user_id integer,
    status_updated_at timestamp without time zone,
    status_updated_by_user_id integer,
    CONSTRAINT testapp_appointments_status_check CHECK ((status = ANY (ARRAY['planned'::text, 'done'::text, 'canceled'::text])))
);


--
-- Name: testapp_appointments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.testapp_appointments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: testapp_appointments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.testapp_appointments_id_seq OWNED BY public.testapp_appointments.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: testapp_appointments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.testapp_appointments ALTER COLUMN id SET DEFAULT nextval('public.testapp_appointments_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: testapp_appointments testapp_appointments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.testapp_appointments
    ADD CONSTRAINT testapp_appointments_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict 30IyscYGXu4Am5h81nVttANDd0LrxBghsMCthBfLVc5CMxORSHqyaBDbWYPTQ7G
