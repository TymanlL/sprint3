# Sprint3 - Environment Configuration

This repository contains environment configuration files for the Sprint3 project across different deployment environments.

## Environment Files

The following environment configuration files are available:

- **`.env.example`** - Template file with all available environment variables and their descriptions
- **`.env.development`** - Development environment configuration
- **`.env.staging`** - Staging/pre-production environment configuration
- **`.env.production`** - Production environment configuration

## Quick Start

### For Development

1. Copy the development environment file:
   ```bash
   cp .env.development .env
   ```

2. Update the `.env` file with your local configuration values

3. Start your application (it will automatically load `.env`)

### For Staging/Production

1. Copy the appropriate environment file:
   ```bash
   # For staging
   cp .env.staging .env

   # For production
   cp .env.production .env
   ```

2. **CRITICAL**: Replace all `CHANGE_ME_*` values with actual credentials

3. Ensure the `.env` file is properly secured and not committed to version control

## Environment Variables Overview

### Application Settings
- `NODE_ENV` - Environment mode (development/staging/production)
- `APP_NAME` - Application name
- `APP_PORT` - Port the application runs on
- `APP_URL` - Full URL of the application

### Database Configuration
- `DB_HOST` - Database host address
- `DB_PORT` - Database port
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `DB_SSL` - Enable SSL for database connections

### Redis Configuration
- `REDIS_HOST` - Redis server host
- `REDIS_PORT` - Redis server port
- `REDIS_PASSWORD` - Redis password (if authentication is enabled)

### Authentication & Security
- `JWT_SECRET` - Secret key for JWT token signing
- `JWT_EXPIRES_IN` - JWT token expiration time
- `BCRYPT_ROUNDS` - Number of bcrypt rounds for password hashing
- `SESSION_SECRET` - Secret key for session management

### External Services
- API keys for Stripe, SendGrid, AWS, etc.
- OAuth credentials for Google, GitHub, etc.
- SMTP configuration for email sending

### Feature Flags
- `ENABLE_REGISTRATION` - Enable/disable user registration
- `ENABLE_EMAIL_VERIFICATION` - Require email verification
- `ENABLE_TWO_FACTOR_AUTH` - Enable two-factor authentication
- `ENABLE_API_RATE_LIMIT` - Enable API rate limiting

## Security Best Practices

1. **Never commit `.env` files** - The `.gitignore` file is configured to exclude `.env` files
2. **Use strong secrets in production** - Generate secrets using:
   ```bash
   openssl rand -base64 64
   ```
3. **Rotate credentials regularly** - Especially for production environments
4. **Use environment-specific credentials** - Don't reuse keys across environments
5. **Limit access** - Only authorized personnel should have access to production credentials
6. **Use secret management tools** - Consider using AWS Secrets Manager, HashiCorp Vault, etc.

## Environment-Specific Settings

### Development
- Lower bcrypt rounds for faster development
- Debug logging enabled
- Mock external APIs to avoid unnecessary API calls
- Relaxed CORS settings
- Email sent to development SMTP (like Mailtrap)

### Staging
- Production-like configuration
- Test API keys (Stripe test mode, etc.)
- Moderate logging
- All features enabled for testing
- Separate database from production

### Production
- Maximum security settings
- Live API keys
- Minimal logging (errors only)
- Strict CORS settings
- High bcrypt rounds
- All monitoring and analytics enabled

## Loading Environment Variables

### Node.js
```javascript
require('dotenv').config();

const dbHost = process.env.DB_HOST;
const dbPort = process.env.DB_PORT;
```

### Using dotenv-flow for automatic environment detection
```bash
npm install dotenv-flow
```

```javascript
require('dotenv-flow').config();
// Automatically loads .env.development in development, etc.
```

### Docker
```dockerfile
# Using environment file in Docker
docker run --env-file .env.production your-image
```

### Docker Compose
```yaml
services:
  app:
    env_file:
      - .env.production
```

## Environment Variable Validation

Consider using a validation library to ensure all required variables are set:

```javascript
const requiredEnvVars = [
  'DB_HOST',
  'DB_PORT',
  'DB_NAME',
  'JWT_SECRET',
];

requiredEnvVars.forEach((varName) => {
  if (!process.env[varName]) {
    throw new Error(`Environment variable ${varName} is required but not set`);
  }
});
```

## Troubleshooting

### Variables not loading
- Ensure `.env` file is in the project root
- Check that `dotenv` is loaded before accessing variables
- Verify there are no syntax errors in the `.env` file

### Values not updating
- Restart your application after changing `.env` files
- Clear any caches
- Check for environment variables set at system level (they override `.env`)

## Contributing

When adding new environment variables:
1. Add them to `.env.example` with documentation
2. Add them to all environment-specific files
3. Update this README with the new variable description
4. Set appropriate default values for each environment

## Support

For questions or issues related to environment configuration, please open an issue in the repository.
