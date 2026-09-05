{{ config(severity='warn') }}

-- If any (symbol, date) has actually been restated more than once, at least one
-- of them should show int_ohlcv_pit.close != fact_ohlcv.close - otherwise the
-- first-observed selection isn't doing anything different from is_latest, which
-- would mean this whole PIT model is silently a no-op duplicate. Warn (not
-- error) severity: this is data-dependent and can be legitimately vacuous if the
-- current dataset has no multi-restated rows yet, same posture as this
-- project's existing assert_market_cap_matches_index_membership precedent.
select 1 as no_differing_restated_row_found
where (select count(*) from {{ ref('fact_restatement_history') }} where restatement_count > 1) > 0
  and not exists (
      select 1
      from {{ ref('int_ohlcv_pit') }} p
      inner join {{ ref('fact_ohlcv') }} f on p.symbol = f.symbol and p.date = f.date
      inner join {{ ref('fact_restatement_history') }} rh on rh.symbol = p.symbol and rh.date = p.date
      where rh.restatement_count > 1
        and p.close != f.close
  )
