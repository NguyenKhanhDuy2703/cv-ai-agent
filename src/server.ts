import 'reflect-metadata';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ConfigService } from '@nestjs/config';
import * as dotenv from 'dotenv';

dotenv.config();

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const config = app.get(ConfigService);

  // CORS – must be set via env, no fallback hard-code
  const frontendOrigin = config.get<string>('FRONTEND_ORIGIN');
  if (!frontendOrigin) {
    throw new Error('FRONTEND_ORIGIN is not set in .env');
  }
  app.enableCors({ origin: frontendOrigin, credentials: true });

  // Port – must be set via env, no fallback hard-code
  const rawPort = config.get<string | number>('AI_PORT');
  if (!rawPort) {
    throw new Error('AI_PORT is not set in .env');
  }
  const port = typeof rawPort === 'number' ? rawPort : parseInt(rawPort, 10);

  await app.listen(port);
  console.log(`[AI Service] listening on http://localhost:${port}`);
}

bootstrap();
