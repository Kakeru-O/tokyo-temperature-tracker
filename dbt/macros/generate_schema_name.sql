{% macro generate_schema_name(custom_schema_name, node) -%}
  {#-
    dbtのデフォルトでは `target.schema` に `custom_schema_name` を連結します（例: public_mart）。
    このプロジェクトでは `stg/int/mart` のスキーマ名をそのまま使いたいので、
    `+schema:` が指定された場合は、その値をそのまま採用します。
  -#}
  {%- if custom_schema_name is none -%}
    {{ target.schema }}
  {%- else -%}
    {{ custom_schema_name | trim }}
  {%- endif -%}
{%- endmacro %}

