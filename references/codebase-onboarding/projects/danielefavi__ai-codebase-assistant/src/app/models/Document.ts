import {
  Sequelize,
  DataTypes,
  Model,
  InferAttributes,
  InferCreationAttributes,
  CreationOptional,
} from 'sequelize';

import { sequelize } from '#core/database.js';

class Document extends Model<InferAttributes<Document>, InferCreationAttributes<Document>> {
  declare id: CreationOptional<number>;
  declare sha256: string;
  declare filename: string | null;
  declare parentSha256: string | null;
  declare vectorStoreId: string | null;
  declare content: string | null;
  declare metadata: Record<PropertyKey, unknown> | null;
  declare status: string | null;
  declare errorCount: number | null;
  declare operations: Record<string, number> | null;

  static readonly DOCUMENT_STATUS = {
    COMPLETED: 'completed',
    ERROR: 'error',
    LOCKED: 'locked',
    TO_PROCESS: 'to_process'
  };

  static readonly OPERATION_STATUS = {
    ERROR: -1,
    SUCCESS: 1
  };

  async setStatusLock(): Promise<void> {
    await this.setStatus(Document.DOCUMENT_STATUS.LOCKED);
  }

  async operationSuccess(operationName: string): Promise<void> {
    const currentOps = this.operations ? { ...this.operations } : {};
    currentOps[operationName] = Document.OPERATION_STATUS.SUCCESS;
    this.operations = currentOps;

    let allOpsDone = true;
    for (const [_key, val] of Object.entries(this.operations)) {
      if (val !== Document.OPERATION_STATUS.SUCCESS) {
        allOpsDone = false;
        break;
      }
    }

    if (allOpsDone) {
      this.status = Document.DOCUMENT_STATUS.COMPLETED;
    } else if (this.status !== Document.DOCUMENT_STATUS.LOCKED) {
      this.status = Document.DOCUMENT_STATUS.TO_PROCESS;
    }

    await this.save();
  }

  async operationError(operationName: string): Promise<void> {
    const currentOps = this.operations ? { ...this.operations } : {};
    currentOps[operationName] = Document.OPERATION_STATUS.ERROR;
    this.operations = currentOps;
    
    this.status = Document.DOCUMENT_STATUS.ERROR;
    if (!this.errorCount) this.errorCount = 0;
    this.errorCount++;

    await this.save();
  }

  async setStatus(status: string): Promise<void> {
    if (this.status === status) {
      return;
    }

    this.status = status;
    await this.save();
  }

  isStatusLocked(): boolean {
    return this.isStatus(Document.DOCUMENT_STATUS.LOCKED);
  }

  isStatus(status: string) {
    return this.status === status;
  }
}

Document.init({
  id: {
      type: DataTypes.BIGINT,
      autoIncrement: true,
      primaryKey: true,
      allowNull: false
  },
  sha256: {
      type: DataTypes.STRING(64),
      allowNull: false,
      unique: true
  },
  filename: {
      type: DataTypes.STRING(255),
      allowNull: true  
  },
  parentSha256: {
      type: DataTypes.STRING(64), // Should match sha256 length
      allowNull: true,  // Matches 'string | null' property type
  },
  vectorStoreId: {
    type: DataTypes.STRING(64),
    allowNull: true,
  },
  content: {
    type: DataTypes.TEXT,
    allowNull: true  
  },
  metadata: {
      type: DataTypes.JSON,
      allowNull: true,
      get() {
        const rawValue = this.getDataValue('metadata');
        try {
          return typeof rawValue === 'string' ? JSON.parse(rawValue) : rawValue;
        } catch {
          return null;
        }
      }
  },
  status: {
    type: DataTypes.STRING(50),
    allowNull: false,
    defaultValue: Document.DOCUMENT_STATUS.TO_PROCESS
  },
  errorCount: {
    type: DataTypes.TINYINT(),
    defaultValue: 0,
    allowNull: false  
  },
  operations: {
      type: DataTypes.JSON,
      allowNull: true,
      get() {
        const rawValue = this.getDataValue('operations');
        try {
          return typeof rawValue === 'string' ? JSON.parse(rawValue) : rawValue;
        } catch {
          return null;
        }
      }
  }
}, {
  sequelize,
  modelName: 'Document',
  tableName: 'documents',
  timestamps: false,

  indexes: [
    { name: 'idx_filename', fields: ['filename'] },
    { fields: ['parentSha256', 'sha256'] }
  ]
});

export default Document;