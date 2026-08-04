-- ============================================================================
-- OMS-360 Version 1.2 - Migration 004: Item Category + Unit
-- ============================================================================
-- FLAGGED, NOT SILENT: adds TWO new nullable columns (category, unit) to
-- BOTH `items` and `inventory` (they are kept structurally mirrored - see
-- app/models.py) so the Inventory Dashboard's "Update Inventory" dialog can
-- edit them, per Product Owner request (2026-07-27). Both columns are
-- NULLable with no default, so every existing row is unaffected - category/
-- unit simply read as NULL/blank until an admin fills them in via the
-- dialog. This migration does not touch any existing column, row, or
-- table, and does not touch `items`/`inventory` primary keys or any other
-- table.
--
-- 2026-07-27 fix: the original version of this file used
-- "ADD COLUMN IF NOT EXISTS", which requires MySQL 8.0.29+. The Product
-- Owner's live oms360_mysql container rejected it with ERROR 1064 (42000)
-- - a plain syntax error - meaning its MySQL build predates that support.
-- Rewritten below to use plain ADD COLUMN, which is supported by every
-- MySQL 8.0.x build. Consequence: this file is no longer safely re-runnable
-- against a database that already has the columns (a second run will fail
-- with "Duplicate column name", not silently succeed). If you need to
-- re-run it, check first with:
--   DESCRIBE items; DESCRIBE inventory;
-- and drop the ALTER lines for whichever table already has category/unit.
--
-- Apply with (PowerShell - the `<` redirection operator bash/cmd use for
-- stdin does NOT work in PowerShell):
--   Get-Content migrations\004_add_item_category_unit.sql | docker exec -i oms360_mysql mysql -uroot -proot123 oms360_db
--
-- Apply with (bash/cmd):
--   mysql -uroot -p oms360_db < migrations/004_add_item_category_unit.sql
--
-- NOTE for a fresh/new environment: this file is also mounted as an
-- automatic init script in docker-compose.yml (05_item_category_unit.sql),
-- so a brand-new database volume picks it up on first boot with no manual
-- step. It is ONLY for an EXISTING database (already has data, so MySQL's
-- /docker-entrypoint-initdb.d scripts will not re-run) that you need to
-- apply this file manually with the command above.
-- ============================================================================

USE oms360_db;

ALTER TABLE items     ADD COLUMN category VARCHAR(100) NULL AFTER item_name;
ALTER TABLE items     ADD COLUMN unit     VARCHAR(50)  NULL AFTER category;
ALTER TABLE inventory ADD COLUMN category VARCHAR(100) NULL AFTER item_name;
ALTER TABLE inventory ADD COLUMN unit     VARCHAR(50)  NULL AFTER category;
