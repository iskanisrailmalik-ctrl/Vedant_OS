import com.verdant.os.engine.physics.Pendulum
import com.verdant.os.engine.physics.PendulumParameters
import com.verdant.os.engine.physics.PendulumState
import kotlin.math.abs
import kotlin.math.sqrt

private fun checkThat(condition: Boolean, message: String) {
    check(condition) { message }
    println("PASS  $message")
}

private fun energyProxy(state: PendulumState): Float {
    val omegaSquared = 9.81f / 0.45f
    return state.angleRadians * state.angleRadians + state.angularVelocity * state.angularVelocity / omegaSquared
}

fun main() {
    val expectedFrequency = sqrt(9.81f / 0.45f)
    checkThat(abs(Pendulum.naturalFrequency(9.81f, 0.45f) - expectedFrequency) < 0.0001f,
        "natural frequency is computed from gravity and stem length")

    var damped = PendulumState(0.2f, 0f)
    val initialEnergy = energyProxy(damped)
    repeat(300) { damped = Pendulum.advance(damped, 1f / 60f) }
    checkThat(damped.angleRadians.isFinite() && damped.angularVelocity.isFinite(),
        "long simulation stays finite")
    checkThat(energyProxy(damped) < initialEnergy, "damping dissipates the energy proxy")

    val stalled = Pendulum.advance(
        state = PendulumState(0.79f, 7.9f),
        dtSeconds = 0.2f,
        windAngularAcceleration = 100f,
    )
    checkThat(abs(stalled.angleRadians) <= 0.8f && abs(stalled.angularVelocity) <= 8f,
        "frame stall and extreme wind remain bounded")

    var at60 = PendulumState(0.25f, 0.1f)
    var at120 = at60
    repeat(180) { at60 = Pendulum.advance(at60, 1f / 60f) }
    repeat(360) { at120 = Pendulum.advance(at120, 1f / 120f) }
    checkThat(abs(at60.angleRadians - at120.angleRadians) <= 0.002f,
        "60 Hz and 120 Hz angle results remain close")
    checkThat(abs(at60.angularVelocity - at120.angularVelocity) <= 0.02f,
        "60 Hz and 120 Hz velocity results remain close")

    val bounds = Pendulum.advance(
        state = PendulumState(10f, 20f),
        dtSeconds = 0f,
        parameters = PendulumParameters(maxAngleRadians = 0.7f, maxAngularVelocityRadiansPerSecond = 6f),
    )
    checkThat(abs(bounds.angleRadians) <= 0.7f && abs(bounds.angularVelocity) <= 6f,
        "initial state is clamped to configured bounds")

    checkThat(runCatching { Pendulum.naturalFrequency(9.81f, 0f) }.exceptionOrNull() is IllegalArgumentException,
        "invalid stem length is rejected explicitly")
    checkThat(runCatching { Pendulum.advance(PendulumState(Float.NaN, 0f), 0.016f) }.exceptionOrNull() is IllegalArgumentException,
        "non-finite state is rejected explicitly")
    checkThat(runCatching { Pendulum.advance(PendulumState(0f, 0f), Float.POSITIVE_INFINITY) }.exceptionOrNull() is IllegalArgumentException,
        "non-finite timestep is rejected explicitly")
    println("\nPhysics harness: 10/10 checks passed.")
}
