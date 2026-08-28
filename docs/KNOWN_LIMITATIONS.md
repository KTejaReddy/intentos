# Known Limitations

As of IntentOS RC-1, the following limitations are present in the platform by design to ensure stability and compilation speed. These are not bugs, but boundaries of the current architecture.

1. **Strict Standard CRUD Generation Only**
   Custom business logic, calculations, and external API integrations cannot currently be expressed inside IntentLang rule blocks. Custom endpoints are stubbed with `501 Not Implemented` and must be filled manually post-compilation.

2. **No Automated Schema Migrations**
   The compiler generates full `CREATE TABLE` and `CREATE INDEX` schema dumps. It does not diff schemas or generate `ALTER TABLE` statements (like Prisma or Alembic). Reprovisioning compiled applications may result in data loss if manual migrations aren't written.

3. **No If/Else Branching**
   IntentLang rules do not support nested `If/Else` blocks. Actions execute linearly in the order they are declared in a `When` block.

4. **Primitive Arrays Only**
   The database IR generators support basic strings, numbers, dates, booleans, and enums. Nested JSON documents or generic arrays are currently unsupported by the generated SQLAlchemy models.

5. **Token Invalidation**
   The built-in authentication systems rely entirely on client-side JWT deletion. There is currently no server-side token revocation or Redis blacklist cache generated.
