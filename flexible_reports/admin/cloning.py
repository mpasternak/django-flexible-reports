"""Admin glue exposing ``Table.clone()`` and ``Report.clone()`` as a button.

The cloning logic itself lives on the models; this module only wires it into
the change form of a ``ModelAdmin``.
"""

from django.contrib import messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

__all__ = ["CloneAdminMixin"]


class CloneAdminMixin:
    """Adds a "Clone" button to the change form of a model with ``clone()``."""

    change_form_template = "admin/flexible_reports/change_form_with_clone.html"

    def get_urls(self):
        info = self.opts.app_label, self.opts.model_name
        my_urls = [
            path(
                "<path:object_id>/clone/",
                # ``require_POST`` cannot be used as a decorator in the class
                # body: its wrapper is ``inner(request, *args, **kwargs)``, so
                # on an unbound method ``request`` would bind to ``self`` and
                # blow up with an AttributeError instead of returning 405.
                # Here it wraps the *bound* method.
                #
                # ``admin_view`` has to stay on the *outside* so that an
                # anonymous GET is redirected to the login page rather than
                # told 405 (which leaks the existence of the URL); it also
                # adds the ``is_staff`` check, ``never_cache`` and session
                # handling.
                self.admin_site.admin_view(require_POST(self.clone_view)),
                name="%s_%s_clone" % info,
            ),
        ]
        # Our routes must come *first*. ``ModelAdmin.get_urls()`` ends with a
        # backwards-compatibility catch-all ``<path:object_id>/`` and the
        # ``path:`` converter matches slashes, so appending our route would
        # leave it dead: ``<pk>/clone/`` would be swallowed as
        # ``object_id="<pk>/clone"`` and redirected into a 404.
        return my_urls + super().get_urls()

    def clone_view(self, request, object_id):
        # A clone is a brand new object, hence ``add``; ``view`` is required on
        # the source. ``change`` on the source deliberately is not -- this
        # matches the built-in "save as new".
        if not self.has_add_permission(request):
            raise PermissionDenied

        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            raise Http404(
                _("%(name)s object with primary key %(key)r does not exist.")
                % {"name": self.opts.verbose_name, "key": object_id}
            )

        if not self.has_view_permission(request, obj):
            raise PermissionDenied

        new_obj = obj.clone()

        # ``message`` is a required argument, and this structure is what makes
        # the history page render "Added." instead of a raw string.
        self.log_addition(request, new_obj, [{"added": {}}])
        self.message_user(
            request,
            _('Cloned to "%(obj)s".') % {"obj": new_obj},
            messages.SUCCESS,
        )

        info = self.opts.app_label, self.opts.model_name
        if self.has_change_permission(request, new_obj):
            url = reverse(
                "admin:%s_%s_change" % info,
                args=(new_obj.pk,),
                current_app=self.admin_site.name,
            )
        else:
            # Sending the user to a change form they may not open would turn a
            # successful action into a 403; mirrors _response_post_save().
            url = reverse(
                "admin:%s_%s_changelist" % info,
                current_app=self.admin_site.name,
            )
        return HttpResponseRedirect(url)
