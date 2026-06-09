1. **Launch / startup failures** — anything that could crash or hang the app on cold start:
   - Singletons or providers that throw during initialisation
   - Missing or misconfigured platform/environment configuration
   - Assets or resources referenced in code but not registered
   - Dependencies expected to be injected but not overridden

2. **Migration issues** — anything that could break users upgrading from a previous version:
   - Database schema changes without a migration path (new tables, renamed/dropped columns)
   - Persisted data format changes (renamed enum values, new required fields in a stored model)
   - Storage keys that changed meaning or type
   - Scheduled task or notification identifiers that may conflict with older registrations

3. **Platform or environment-specific risks**:
   - Permission or capability differences between platforms
   - Background execution limits
   - OS or runtime version compatibility
   - Missing platform configuration (manifests, entitlements, config files)

4. **State and data consistency risks**:
   - Async operations that are fire-and-forget with no error handling
   - Repository or service methods that can partially succeed
   - Race conditions between concurrent reads and writes

5. **Edge cases in business logic**:
   - Off-by-one errors in date/range boundaries (inclusive vs exclusive ends)
   - Timezone and DST handling in scheduled values
   - Numeric overflow or precision issues
