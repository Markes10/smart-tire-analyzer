package com.example.data

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "tire_scans")
data class TireScan(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val timestamp: Long,
    val title: String,
    val speed: Float,
    val pressure: Float,
    val temperature: Float,
    val wearPattern: String, // "Normal", "Center Wear", "Edge Wear", "Camber Wear", "Cupping Wear"
    val overallHealth: Int, // 0 to 100
    val notes: String,
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val routeName: String = "Pacific Coast Hwy"
)

@Dao
interface TireScanDao {
    @Query("SELECT * FROM tire_scans ORDER BY timestamp DESC")
    fun getAllScans(): Flow<List<TireScan>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertScan(scan: TireScan): Long

    @Query("SELECT * FROM tire_scans WHERE id = :id LIMIT 1")
    suspend fun getScanById(id: Long): TireScan?

    @Query("DELETE FROM tire_scans WHERE id = :id")
    suspend fun deleteScanById(id: Long)
}

@Database(entities = [TireScan::class], version = 1, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun tireScanDao(): TireScanDao
}

class TireScanRepository(private val tireScanDao: TireScanDao) {
    val allScans: Flow<List<TireScan>> = tireScanDao.getAllScans()

    suspend fun insert(scan: TireScan): Long = tireScanDao.insertScan(scan)

    suspend fun getById(id: Long): TireScan? = tireScanDao.getScanById(id)

    suspend fun deleteById(id: Long) = tireScanDao.deleteScanById(id)
}
