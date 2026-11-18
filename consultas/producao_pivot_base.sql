WITH PARAMETROS AS (
    SELECT
        TO_DATE(
            LEFT(CAST(:FtDateInicio AS TEXT), 10),
            CASE
                WHEN CAST(:FtDateInicio AS TEXT) ~ '^[0-9]{8}$'
                    THEN 'YYYYMMDD'
                WHEN LEFT(CAST(:FtDateInicio AS TEXT), 10) LIKE '__/__/____'
                    THEN 'MM/DD/YYYY'
                ELSE 'YYYY-MM-DD'
            END
        ) AS DATA_INICIO,

        TO_DATE(
            LEFT(CAST(:FtDateFim AS TEXT), 10),
            CASE
                WHEN CAST(:FtDateFim AS TEXT) ~ '^[0-9]{8}$'
                    THEN 'YYYYMMDD'
                WHEN LEFT(CAST(:FtDateFim AS TEXT), 10) LIKE '__/__/____'
                    THEN 'MM/DD/YYYY'
                ELSE 'YYYY-MM-DD'
            END
        ) AS DATA_FIM
),

NF AS (
    SELECT
        N.COD_EMPRESA,
        N.MODELO,
        N.SERIE,
        N.SUB_SERIE,
        N.NUMERO,
        N.NUMERO_NFSE,
        N.DT_EMISSAO,
        N.CLIENTE

    FROM TNOTA_FISCAL N

    CROSS JOIN PARAMETROS P

    WHERE N.DT_EMISSAO >= P.DATA_INICIO
      AND N.DT_EMISSAO < P.DATA_FIM + INTERVAL '1 DAY'
),

-- =====================================================
-- ITENS DAS NOTAS FISCAIS
-- =====================================================
ITENS_NF AS (
    SELECT
        N.*,
        'PRODUTO'::TEXT AS TIPO_ITEM,
        I.AUT_ AS AUT_ITEM,
        I.COD_ORCAMENTO,
        I.GUID_ORCAMENTO,
        I.COD_OS AS COD_OS_NF,
        I.COD_PRODUTO,
        I.PRODUTO::TEXT AS DESCRICAO_NF,
        I.QTDE AS QTDE_NF
    FROM NF N
    INNER JOIN TNOTA_FISCAL_ITEM I
        ON I.COD_EMPRESA = N.COD_EMPRESA
       AND I.MODELO = N.MODELO
       AND I.SERIE = N.SERIE
       AND I.SUB_SERIE = N.SUB_SERIE
       AND I.NUMERO_NF = N.NUMERO
       AND I.TP_MOVIMENTO_DEPOSITO = 1

    UNION ALL

    SELECT
        N.*,
        'SERVICO'::TEXT,
        S.AUT_,
        S.COD_ORCAMENTO,
        S.GUID_ORCAMENTO,
        S.COD_OS,
        NULL::INTEGER,
        COALESCE(
            NULLIF(S.PRODUTO, ''),
            S.DISCRIMINACAO_SERVICO,
            S.CODIGO
        )::TEXT,
        S.QTDE
    FROM NF N
    INNER JOIN TNOTA_FISCAL_SERVICO S
        ON S.COD_EMPRESA = N.COD_EMPRESA
       AND S.MODELO = N.MODELO
       AND S.SERIE = N.SERIE
       AND S.SUB_SERIE = N.SUB_SERIE
       AND S.NUMERO_NF = N.NUMERO
),

-- =====================================================
-- ORÇAMENTOS
-- =====================================================
ORCAMENTO_NF AS (
    SELECT
        I.*,
        O.N_ORCAMENTO,
        O.VERSAO,
        O.CLIENTE AS CLIENTE_ORCAMENTO,
        OI.GUID_LINHA,
        OI.DESCRICAO AS ITEM_ORCAMENTO,
        OI.COD_OS AS COD_OS_ORCAMENTO
    FROM ITENS_NF I

    LEFT JOIN TORCAMENTO O
        ON O.COD_EMPRESA = I.COD_EMPRESA
       AND O.CODIGO = I.COD_ORCAMENTO

    LEFT JOIN TORCAMENTO_ITENS OI
        ON OI.COD_EMPRESA = I.COD_EMPRESA
       AND OI.COD_ORCAMENTO = I.COD_ORCAMENTO
       AND OI.GUID_LINHA = I.GUID_ORCAMENTO
       AND (
            I.TIPO_ITEM = 'SERVICO'
            OR OI.COD_PRODUTO = I.COD_PRODUTO
       )
),

-- =====================================================
-- VÍNCULOS COM AS OS
-- =====================================================
VINCULOS_OS AS (
    SELECT
        I.COD_EMPRESA,
        I.TIPO_ITEM,
        I.AUT_ITEM,
        OS.CODIGO AS COD_OS,
        'ORCAMENTO'::TEXT AS ORIGEM
    FROM ORCAMENTO_NF I

    INNER JOIN TSOL_MAX_OS SM
        ON SM.COD_EMPRESA = I.COD_EMPRESA
       AND SM.GUID_LM = I.GUID_LINHA

    INNER JOIN TOS_SOLICITACAO_NECESSIDADE SN
        ON SN.COD_EMPRESA = SM.COD_EMPRESA
       AND SN.GUID_SOLICITACAO = SM.GUID_PAI

    INNER JOIN TOS OS
        ON OS.COD_EMPRESA = SN.COD_EMPRESA
       AND OS.CODIGO = SN.COD_OS

    UNION ALL

    SELECT
        I.COD_EMPRESA,
        I.TIPO_ITEM,
        I.AUT_ITEM,
        OS.CODIGO,
        'NOTA_FISCAL'::TEXT
    FROM ORCAMENTO_NF I

    INNER JOIN TOS OS
        ON OS.COD_EMPRESA = I.COD_EMPRESA
       AND OS.CODIGO = I.COD_OS_NF

    UNION ALL

    SELECT
        I.COD_EMPRESA,
        I.TIPO_ITEM,
        I.AUT_ITEM,
        OS.CODIGO,
        'ITEM_ORCAMENTO'::TEXT
    FROM ORCAMENTO_NF I

    INNER JOIN TOS OS
        ON OS.COD_EMPRESA = I.COD_EMPRESA
       AND OS.CODIGO = I.COD_OS_ORCAMENTO
),

-- =====================================================
-- ELIMINAR DUPLICIDADE DE OS
-- =====================================================
OS_DISTINTAS AS (
    SELECT
        COD_EMPRESA,
        TIPO_ITEM,
        AUT_ITEM,
        COD_OS,
        STRING_AGG(
            DISTINCT ORIGEM,
            ' / '
        ) AS ORIGEM_VINCULO
    FROM VINCULOS_OS
    GROUP BY
        COD_EMPRESA,
        TIPO_ITEM,
        AUT_ITEM,
        COD_OS
)

-- =====================================================
-- RESULTADO FINAL
-- =====================================================
SELECT
    COALESCE(
        NULLIF(I.NUMERO_NFSE::TEXT, ''),
        I.NUMERO::TEXT
    ) AS NOTA_FISCAL,

    TO_CHAR(
        I.DT_EMISSAO,
        'DD/MM/YYYY'
    ) AS EMISSAO_NF,

    COALESCE(
        NULLIF(TRIM(I.CLIENTE), ''),
        NULLIF(TRIM(I.CLIENTE_ORCAMENTO), ''),
        NULLIF(TRIM(OS.CLIENTE), '')
    ) AS CLIENTE,

    I.DESCRICAO_NF,

    I.N_ORCAMENTO,

    I.VERSAO AS VERSAO_ORCAMENTO,

    OS.N_OS AS OS_PRINCIPAL,

    OS.U_CLASSIFICACAO AS SEGMENTO,

    -- =================================================
    -- MATERIAIS PRÓPRIOS DA OS PRINCIPAL
    -- =================================================
    M.COD_INTERNO AS COD_PRODUTO_PROPRIO,

    M.PRODUTO AS PRODUTO_PROPRIO,

    M.UNIDADE AS UNIDADE,

    M.QTDE_UTILIZADA,

    -- =================================================
    -- OS DE FABRICAÇÃO
    -- =================================================
    FAB.N_OS AS OS_FABRICACAO,

    -- =================================================
    -- MATERIAIS PRÓPRIOS DA OS DE FABRICAÇÃO
    -- =================================================
    MF.COD_INTERNO AS COD_MATERIAL_FABRICACAO,

    MF.PRODUTO AS MATERIAL_FABRICACAO,

    MF.UNIDADE AS UNIDADE_MATERIAL,

    MF.QTDE_UTILIZADA AS QTDE_UTILIZADA_FABRICACAO

FROM ORCAMENTO_NF I

-- =====================================================
-- OS VINCULADAS À NOTA
-- =====================================================
INNER JOIN OS_DISTINTAS V
    ON V.COD_EMPRESA = I.COD_EMPRESA
   AND V.TIPO_ITEM = I.TIPO_ITEM
   AND V.AUT_ITEM = I.AUT_ITEM

INNER JOIN TOS OS
    ON OS.COD_EMPRESA = V.COD_EMPRESA
   AND OS.CODIGO = V.COD_OS

-- =====================================================
-- MATERIAIS DA OS PRINCIPAL
--
-- LEFT JOIN:
-- MANTÉM A OS MESMO SEM MATERIAL PRÓPRIO
--
-- EXISTS:
-- TRAZ SOMENTE PRODUÇÃO PRÓPRIA
-- =====================================================
LEFT JOIN TLIS_MAT M
    ON M.COD_EMPRESA = OS.COD_EMPRESA
   AND M.COD_OS = OS.CODIGO
   AND COALESCE(M.GERA_EST_PP_AUTO, 0) <> 1

   AND EXISTS (
       SELECT 1
       FROM TPRODUTO P
       WHERE P.COD_EMPRESA = M.COD_EMPRESA
         AND P.CODIGO = M.COD_PRODUTO
         AND P.METODO_REPOSICAO = 1
   )

-- =====================================================
-- LOCALIZAR OS DE FABRICAÇÃO DO MATERIAL PRÓPRIO
-- =====================================================
LEFT JOIN LATERAL (
    SELECT DISTINCT
        OS_FAB.COD_EMPRESA,
        OS_FAB.CODIGO,
        OS_FAB.N_OS,
        OS_FAB.TITULO,
        OS_FAB.U_CLASSIFICACAO

    FROM TSOL_MAX_OS SM_FAB

    INNER JOIN TOS_SOLICITACAO_NECESSIDADE SN_FAB
        ON SN_FAB.COD_EMPRESA = SM_FAB.COD_EMPRESA
       AND SN_FAB.GUID_SOLICITACAO = SM_FAB.GUID_PAI

    INNER JOIN TOS OS_FAB
        ON OS_FAB.COD_EMPRESA = SN_FAB.COD_EMPRESA
       AND OS_FAB.CODIGO = SN_FAB.COD_OS

    WHERE SM_FAB.COD_EMPRESA = M.COD_EMPRESA
      AND SM_FAB.GUID_LM = M.GUID_LINHA
      AND OS_FAB.CODIGO <> OS.CODIGO

      AND (
          SM_FAB.COD_PRODUTO IS NULL
          OR M.COD_PRODUTO IS NULL
          OR SM_FAB.COD_PRODUTO = M.COD_PRODUTO
      )

) FAB ON TRUE

-- =====================================================
-- MATERIAIS DA OS DE FABRICAÇÃO
--
-- MANTÉM A OS MESMO SEM MATERIAIS PRÓPRIOS
-- =====================================================
LEFT JOIN TLIS_MAT MF
    ON MF.COD_EMPRESA = FAB.COD_EMPRESA
   AND MF.COD_OS = FAB.CODIGO
   AND COALESCE(MF.GERA_EST_PP_AUTO, 0) <> 1

   AND EXISTS (
       SELECT 1
       FROM TPRODUTO PF
       WHERE PF.COD_EMPRESA = MF.COD_EMPRESA
         AND PF.CODIGO = MF.COD_PRODUTO
         AND PF.METODO_REPOSICAO = 1
   )

-- =====================================================
-- ORDENAÇÃO
-- =====================================================
ORDER BY
    I.COD_EMPRESA,
    I.N_ORCAMENTO,
    OS.N_OS,
    M.COD_INTERNO,
    FAB.N_OS,
    MF.COD_INTERNO;
