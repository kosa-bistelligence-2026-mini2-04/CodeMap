import { Logger } from '@nestjs/common'
import { NestFactory } from '@nestjs/core'
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger'
import { AppModule } from './app.module'

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bodyParser: false,
  })

  app.enableCors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') ?? [
      'http://localhost:3000',
      'http://localhost:3001',
    ],
    credentials: true,
  })

  const isDevelopment = process.env.NODE_ENV !== 'production'

  if (isDevelopment) {
    const config = new DocumentBuilder()
      .setTitle('API')
      .setDescription('Backend API')
      .setVersion('1.0')
      .addBearerAuth()
      .build()

    const document = SwaggerModule.createDocument(app, config)
    SwaggerModule.setup('docs', app, document)
  }

  const port = Number(process.env.PORT ?? 4000)
  await app.listen(port)
  Logger.log(`Application running on port ${port}`, 'Bootstrap')
}

bootstrap()
