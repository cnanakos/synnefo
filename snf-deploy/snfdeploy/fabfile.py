# Too many lines in module pylint: disable-msg=C0302
# Too many arguments (7/5) pylint: disable-msg=R0913

# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Fabric file for snf-deploy

"""

from __future__ import with_statement
from fabric.api import env, execute, parallel
from snfdeploy import context
from snfdeploy import constants
from snfdeploy import roles
import copy


def with_ctx(fn):
    def wrapper(*args):
        ctx = context.Context()
        return fn(*args, ctx=ctx)
    return wrapper


def with_cluster(fn):
    def wrapper(old_ctx, *args):
        ctx = copy.deepcopy(old_ctx)
        ctx.update(cluster=env.host)
        return fn(ctx, *args)
    return wrapper


def with_node(fn):
    def wrapper(old_ctx, *args):
        ctx = copy.deepcopy(old_ctx)
        ctx.update(node=env.host)
        return fn(ctx, *args)
    return wrapper


def setup_env(args):
    env.component = args.component
    env.method = args.method
    env.role = args.role
    env.cluster = args.cluster
    env.node = args.node


# Helper methods that are invoked via fabric's execute

@parallel
@with_node
def _setup_vmc(ctx):
    VMC = roles.get(constants.VMC, ctx)
    VMC.setup()


@with_node
def _setup_master(ctx):
    MASTER = roles.get(constants.MASTER, ctx)
    MASTER.setup()


@with_node
def _setup_role(ctx, role):
    ROLE = roles.get(role, ctx)
    ROLE.setup()


@parallel
@with_cluster
def _setup_cluster(ctx):
    execute(_setup_master, ctx, hosts=ctx.masters)
    execute(_setup_vmc, ctx, hosts=ctx.vmcs)


# Helper method that get a context snapshot and
# invoke fabric's execute with proper host argument

@with_ctx
def setup_role(role, ctx=None):
    execute(_setup_role, ctx, role, hosts=ctx.get(role))


@with_ctx
def setup_cluster(ctx=None):
    execute(_setup_cluster, ctx, hosts=ctx.clusters)


def setup_synnefo():
    setup_role(constants.NS)
    setup_role(constants.NFS)
    setup_role(constants.DB)
    setup_role(constants.MQ)

    setup_role(constants.ASTAKOS)
    setup_role(constants.PITHOS)
    setup_role(constants.CYCLADES)
    setup_role(constants.CMS)

    setup_cluster()

    setup_role(constants.STATS)
    setup_role(constants.CLIENT)


def setup_ganeti():
    setup_role(constants.NS)
    setup_role(constants.NFS)
    setup_cluster()


@with_cluster
def _setup_qa(ctx):
    setup_role(constants.NS)
    setup_role(constants.NFS)
    setup_cluster()
    setup_role(constants.DEV)


@with_ctx
def setup_qa(ctx=None):
    execute(_setup_qa, ctx, hosts=ctx.clusters)


@with_ctx
def setup(ctx=None):

    if env.node:
        if env.component:
            C = roles.get(env.component, ctx)
        elif env.role:
            C = roles.get(env.role, ctx)
        if env.method:
            fn = getattr(C, env.method)
            fn()
        else:
            C.setup()

    elif env.cluster:
        _setup_cluster(ctx)
