CREATE OR REPLACE VIEW public.wms_aeropuerto AS
 SELECT docto_id,
    referencia,
    (
        CASE
            WHEN (fecha ~ '^\d{4}-\d{2}-\d{2}'::text) THEN (fecha)::timestamp without time zone
            ELSE NULL::timestamp without time zone
        END)::date AS fecha,
    (
        CASE
            WHEN (fecha ~ '^\d{4}-\d{2}-\d{2}'::text) THEN (fecha)::timestamp without time zone
            ELSE NULL::timestamp without time zone
        END)::time without time zone AS hora,
    cliente,
    cantidad_pedida,
    cantidad_surtida,
    tarimas,
    tasa_de_cumplimiento,
    estado
   FROM wms_aeropuerto_raw
  WHERE ((referencia !~~ 'INV%'::text) AND (estado <> 'EMBARCADO'::text));;