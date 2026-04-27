# CLI & Tools

## sqlcmd (Classic)

```bash
# Connect with Windows auth
sqlcmd -S myserver -d MyDB -E

# Connect with SQL auth
sqlcmd -S myserver,1433 -U myuser -P 'mypassword' -d MyDB

# Run inline query
sqlcmd -S myserver -d MyDB -Q "SELECT TOP 10 * FROM Orders"

# Run a .sql file
sqlcmd -S myserver -d MyDB -i "C:\Scripts\deploy.sql" -o "C:\Logs\output.txt"

# Variable substitution
sqlcmd -S myserver -d MyDB -v TableName="Orders" MaxRows="100" \
    -Q "SELECT TOP $(MaxRows) * FROM $(TableName)"

# CSV-style output
sqlcmd -S myserver -d MyDB -Q "SELECT OrderID, Total FROM Orders" \
    -s "," -W -h -1 -o results.csv

# Batch separator and error handling
sqlcmd -S myserver -d MyDB -i deploy.sql -b  # -b = abort on error
```

### sqlcmd Script Mode

```sql
-- Inside a .sql file run by sqlcmd
:setvar DatabaseName "MyDB"
:setvar SchemaVersion "2.5"

USE [$(DatabaseName)];
GO

PRINT 'Deploying schema version $(SchemaVersion)';
GO

:r "tables.sql"       -- include another file
:r "procedures.sql"

-- Conditional execution
:on error exit         -- stop on error
:on error ignore       -- continue on error
```

---

## sqlcmd (Go-Based, Cross-Platform)

Modern replacement available on Windows, macOS, and Linux.

```bash
# Install
# Windows: winget install sqlcmd
# macOS:   brew install sqlcmd
# Linux:   curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
#          sudo apt-get install sqlcmd

# Azure AD / Entra ID interactive auth
sqlcmd -S myserver.database.windows.net --authentication-method ActiveDirectoryInteractive

# Managed Identity
sqlcmd -S myserver.database.windows.net --authentication-method ActiveDirectoryManagedIdentity

# Create a local SQL Server container
sqlcmd create mssql --accept-eula --using https://aka.ms/AdventureWorksLT.bak

# Open interactive session with syntax highlighting
sqlcmd open

# Query with --format for structured output
sqlcmd -S myserver -d MyDB --format json \
    -Q "SELECT TOP 5 OrderID, Total FROM Orders"
```

---

## SSMS (SQL Server Management Studio)

### Key Features

- **Object Explorer**: browse server objects, script out DDL
- **Execution Plan Viewer**: graphical actual/estimated plans (Ctrl+M for actual plan)
- **Activity Monitor**: real-time overview of processes, waits, I/O, queries
- **Query Store reports**: top resource consumers, regressed queries, plan comparison
- **IntelliSense**: code completion (Ctrl+Shift+R to refresh cache)
- **Template Explorer**: templates for common DDL/DML patterns

### Execution Plan Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+L | Display estimated execution plan |
| Ctrl+M | Include actual execution plan (then F5) |
| Ctrl+Shift+F5 | Clear estimated plan cache |

### Useful SSMS Options

```text
Tools → Options → Query Execution → SQL Server → Advanced
  → SET STATISTICS IO: ON
  → SET STATISTICS TIME: ON

Tools → Options → Query Results → SQL Server → Results to Grid
  → Maximum Characters Retrieved: 65535 (for large text/JSON)
```

---

## Azure Data Studio

Cross-platform, lightweight editor for SQL Server and Azure databases.

### Key Features

- **SQL Notebooks**: mix SQL, Markdown, and results in a single document
- **Extensions**: PostgreSQL, MySQL, schema compare, dacpac, admin pack
- **Integrated terminal**: run sqlcmd, PowerShell, bash alongside queries
- **Dashboard widgets**: customizable server/database dashboards

### SQL Notebook Example

```sql
-- Cell 1: Markdown
-- # Daily Health Check

-- Cell 2: SQL
SELECT @@VERSION AS ServerVersion;

-- Cell 3: SQL
SELECT name, state_desc, recovery_model_desc
FROM sys.databases
ORDER BY name;

-- Cell 4: SQL
EXEC sp_whoisactive;
```

### Useful Extensions

```bash
# Install from command palette (Ctrl+Shift+P → "Install Extension")
# - SQL Server Schema Compare
# - SQL Database Projects
# - Admin Pack for SQL Server (sp_whoisactive, diagnostics)
# - PostgreSQL (for multi-database shops)
```

---

## dbatools (PowerShell)

Comprehensive SQL Server automation with 500+ commands.

```powershell
# Install
Install-Module dbatools -Scope CurrentUser

# Connect and test
Connect-DbaInstance -SqlInstance myserver
Test-DbaConnection -SqlInstance myserver

# Backup and restore
Backup-DbaDatabase -SqlInstance myserver -Database MyDB -Path \\share\backups -Type Full
Restore-DbaDatabase -SqlInstance myserver -Path \\share\backups\MyDB_Full.bak

# Migrate an entire instance
Copy-DbaDatabase -Source OldServer -Destination NewServer -Database MyDB -BackupRestore -SharedPath \\share\migration

# Find and fix orphaned users
Repair-DbaDbOrphanUser -SqlInstance myserver -Database MyDB

# Run best practice checks
Invoke-DbaDiagnosticQuery -SqlInstance myserver | Export-Csv diagnostics.csv
Invoke-DbaCheck -SqlInstance myserver -Check DatabaseStatus, LastBackup, FailedJob

# Index maintenance
Get-DbaDbIndex -SqlInstance myserver -Database MyDB |
    Where-Object { $_.FragmentationPercent -gt 30 } |
    ForEach-Object { $_.Rebuild() }

# Export / import data
Write-DbaDbTableData -SqlInstance myserver -Database MyDB -Table Staging -InputObject $csvData

# Monitor
Watch-DbaDbLogin -SqlInstance myserver   # watch login attempts
Get-DbaProcess -SqlInstance myserver     # view sessions
Get-DbaWaitStatistic -SqlInstance myserver # wait stats
```

---

## sp_whoisactive

Real-time session monitoring by Adam Mechanic.

```sql
-- Install (download from http://whoisactive.com or via dbatools)
-- Install-DbaWhoIsActive -SqlInstance myserver -Database master

-- Basic usage
EXEC sp_whoisactive;

-- With additional details
EXEC sp_whoisactive
    @get_plans = 1,             -- include execution plans
    @get_full_inner_text = 1,   -- full query text (not just current statement)
    @get_locks = 1,             -- lock details
    @sort_order = '[cpu] DESC'; -- sort by CPU

-- Filter to specific database
EXEC sp_whoisactive
    @filter_type = 'database',
    @filter = 'MyDB';

-- Capture to a table for historical analysis
DECLARE @destination TABLE (
    [dd hh:mm:ss.mss] VARCHAR(20), session_id INT, sql_text XML,
    login_name NVARCHAR(128), wait_info NVARCHAR(4000),
    CPU INT, tempdb_allocations BIGINT, reads BIGINT, writes BIGINT,
    [status] VARCHAR(30), blocking_session_id INT
);

EXEC sp_whoisactive @destination_table = '#WhoIsActive';
-- Or log periodically via SQL Agent job
```

---

## Ola Hallengren Maintenance Solution

Industry-standard maintenance scripts for backups, integrity checks, and index optimization.

```sql
-- Install: https://ola.hallengren.com
-- Or via dbatools: Install-DbaMaintenanceSolution -SqlInstance myserver -Database master

-- Full backup of all user databases
EXEC dbo.DatabaseBackup
    @Databases = 'USER_DATABASES',
    @Directory = 'D:\Backups',
    @BackupType = 'FULL',
    @Compress = 'Y',
    @CheckSum = 'Y',
    @CleanupTime = 168;  -- delete backups older than 7 days (hours)

-- Transaction log backup every 15 minutes
EXEC dbo.DatabaseBackup
    @Databases = 'USER_DATABASES',
    @Directory = 'D:\Backups',
    @BackupType = 'LOG',
    @Compress = 'Y',
    @CleanupTime = 72;

-- Index optimization (smart rebuild/reorganize)
EXEC dbo.IndexOptimize
    @Databases = 'USER_DATABASES',
    @FragmentationLow = NULL,                        -- skip low fragmentation
    @FragmentationMedium = 'INDEX_REORGANIZE',       -- 10-30%
    @FragmentationHigh = 'INDEX_REBUILD_ONLINE',     -- >30%
    @FragmentationLevel1 = 10,
    @FragmentationLevel2 = 30,
    @UpdateStatistics = 'ALL',
    @OnlyModifiedStatistics = 'Y';

-- Integrity check (weekly)
EXEC dbo.DatabaseIntegrityCheck
    @Databases = 'USER_DATABASES',
    @CheckCommands = 'CHECKDB';

-- View maintenance log
SELECT * FROM dbo.CommandLog ORDER BY StartTime DESC;
```

### Recommended Agent Job Schedule

| Job | Frequency | Time |
|---|---|---|
| Full backup | Daily | 11:00 PM |
| Diff backup | Every 4 hours | 3,7,11 AM/PM |
| Log backup | Every 15 min | Continuous |
| CHECKDB | Weekly (Sunday) | 2:00 AM |
| Index optimize | Weekly (Saturday) | 10:00 PM |
| Statistics update | Daily | After index optimize |
