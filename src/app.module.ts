// src/app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AiController } from './routes/ai.routes';
import { CoreAIClient } from './core/coreAI.client';
import { AIModelClient } from './core/model-client.interface';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      cache: true,
      envFilePath: '.env',
    }),
  ],
  controllers: [AiController],
  providers: [
    {
      provide: 'AI_MODEL_CLIENT',
      useFactory: (_cfg: ConfigService): AIModelClient => {
        return new CoreAIClient();
      },
      inject: [ConfigService],
    },
  ],
})
export class AppModule {}
