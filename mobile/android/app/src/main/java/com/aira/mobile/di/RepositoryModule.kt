package com.aira.mobile.di

import com.aira.mobile.data.repository.AgentRepositoryImpl
import com.aira.mobile.domain.repository.AgentRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindAgentRepository(
        agentRepositoryImpl: AgentRepositoryImpl
    ): AgentRepository
}
