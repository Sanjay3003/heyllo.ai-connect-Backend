-- Migration: Add AI Configuration Table
-- Created: 2026-01-05
-- Description: Creates the ai_configurations table for storing AI agent settings per tenant

-- Create the ai_configurations table
CREATE TABLE IF NOT EXISTS ai_configurations (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) UNIQUE NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    system_prompt TEXT,
    opening_line VARCHAR(500),
    voice VARCHAR(50) DEFAULT 'nat',
    speed VARCHAR(20) DEFAULT 'normal',
    tone VARCHAR(20) DEFAULT 'professional',
    language VARCHAR(10) DEFAULT 'en-US',
    max_duration VARCHAR(10) DEFAULT '300',
    temperature VARCHAR(10) DEFAULT '0.7',
    wait_for_greeting VARCHAR(10) DEFAULT 'true',
    record_calls VARCHAR(10) DEFAULT 'true',
    intent_actions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index on tenant_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_configurations_tenant_id ON ai_configurations(tenant_id);

-- Add comment
COMMENT ON TABLE ai_configurations IS 'Stores AI agent configuration settings per tenant';

-- Rollback script (if needed):
-- DROP TABLE IF EXISTS ai_configurations;
