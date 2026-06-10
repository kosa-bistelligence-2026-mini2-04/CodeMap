import { Sequelize, Dialect } from 'sequelize';
import dotenv from 'dotenv';

dotenv.config();

const { DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_DIALECT } = process.env;

const requiredEnvVars: { name: string; value: string | undefined }[] = [
    { name: 'DB_NAME', value: DB_NAME },
    { name: 'DB_USER', value: DB_USER },
    { name: 'DB_PASS', value: DB_PASS },
    { name: 'DB_HOST', value: DB_HOST },
    { name: 'DB_DIALECT', value: DB_DIALECT },
];

const missingVars = requiredEnvVars
    .filter(v => v.value === undefined || v.value === null || v.value === '')
    .map(v => v.name);

if (missingVars.length > 0) {
    console.error(`Error: Missing required databa4se environment variables: ${missingVars.join(', ')}`);
    process.exit(1);
}

// Validate DB_DIALECT: sequelize supports specific dialect strings.
const supportedDialects: Dialect[] = ['mysql', 'postgres', 'sqlite', 'mariadb', 'mssql', 'db2', 'snowflake', 'oracle'];
if (!supportedDialects.includes(DB_DIALECT as Dialect)) {
    console.error(`Error: Unsupported DB_DIALECT specified: "${DB_DIALECT}". Must be one of: ${supportedDialects.join(', ')}`);
    process.exit(1);
}

let dbPort: number | undefined = undefined;
const defaultPort = 3306;

if (DB_PORT) {
    dbPort = parseInt(DB_PORT, 10);
    if (isNaN(dbPort)) {
        console.error(`Error: Invalid DB_PORT: "${DB_PORT}". Must be a valid number.`);
        process.exit(1);
    }
}

const sequelize = new Sequelize(DB_NAME!, DB_USER!, DB_PASS!, {
    host: DB_HOST!,
    port: dbPort || defaultPort,
    dialect: DB_DIALECT as Dialect,
    logging: process.env.NODE_ENV === 'development' ? console.log : false,
    pool: {
        max: 10, // Max number of connections in pool
        min: 0,  // Min number of connections in pool
        acquire: 30000, // Max time (ms) pool tries to get connection before throwing error
        idle: 10000     // Max time (ms) a connection can be idle before being released
    }
});

/**
 * Asynchronously tests the database connection using sequelize.authenticate().
 * Logs the outcome to the console.
 */
async function testDbConnection(): Promise<void> {
    try {
        await sequelize.authenticate();
        console.log('Database connection established successfully.');
    } catch (error: unknown) {
        console.error('Unable to connect to the database:');
        if (error instanceof Error) {
            console.error(`   Error: ${error.message}`);
            console.error(error.stack);
        } else {
            console.error(error);
        }
        process.exit(1);
    }
}

export { sequelize, testDbConnection };